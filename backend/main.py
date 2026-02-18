"""FastAPI application entry point for the DexIQ AI Presenter.

Orchestrates the presentation: receives commands from Chainlit,
processes them through the LangGraph state machine, and sends
actions to the presenter screen via WebSocket.
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.agent.commands import Command, CommandQueue, parse_command
from backend.agent.graph import presentation_graph
from backend.agent.states import GraphState, create_initial_state
from backend.models.presentation import AgentState
from backend.routers import audience, control, presenter, tts
from backend.services.llm_service import (
    filter_question as llm_filter_question,
    generate_audience_response,
    generate_qa_answer,
)
from backend.services.question_manager import QuestionManager
from backend.services.tts_service import (
    is_configured as tts_is_configured,
    stream_speech_as_base64,
    synthesize_speech,
)

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# --- Global State ---
command_queue = CommandQueue()
question_manager = QuestionManager()
presentation_state: GraphState = create_initial_state()

# Pending command queue — holds one command to auto-execute when audio finishes
_pending_queued_command: dict | None = None
# Active playback token — used to ignore stale audio_ended events
_active_playback_token: str | None = None

# Presentation config cache
_presentation_config: dict = {}
_audience_config: dict = {}


def _load_audience_config() -> dict:
    """Load audience roster from config/audience.yaml."""
    global _audience_config
    if _audience_config:
        return _audience_config

    config_path = Path(__file__).parent.parent / "config" / "audience.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            _audience_config = {
                member["name"].lower(): member
                for member in data.get("audience", [])
            }
    except FileNotFoundError:
        logger.warning(f"Audience config not found at {config_path}")
        _audience_config = {}

    return _audience_config


def _load_presentation_config() -> dict:
    """Load presentation config for audio file validation."""
    global _presentation_config
    if _presentation_config:
        return _presentation_config

    config_path = Path(__file__).parent.parent / "config" / "presentation.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            _presentation_config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Presentation config not found at {config_path}")
        _presentation_config = {}

    return _presentation_config


def _validate_audio_files():
    """Check which pre-generated audio files exist and warn about missing ones."""
    config = _load_presentation_config()
    audio_dir = Path(__file__).parent.parent / "frontend" / "audio"
    slides = config.get("slides", [])

    expected = []
    for slide in slides:
        audio_file = slide.get("audio_file")
        if audio_file:
            expected.append((slide.get("id", "?"), slide.get("title", ""), Path(audio_file).name))

        interaction = slide.get("interaction")
        if interaction:
            q_audio = interaction.get("question_audio")
            if q_audio:
                expected.append((slide.get("id", "?"), f"{slide.get('title', '')} (ask)", Path(q_audio).name))

    found = 0
    missing = []
    for slide_id, title, filename in expected:
        if (audio_dir / filename).exists():
            found += 1
        else:
            missing.append((slide_id, title, filename))

    logger.info(f"Audio files: {found}/{len(expected)} present.")
    if missing:
        logger.warning(f"Missing {len(missing)} audio file(s):")
        for sid, title, fname in missing:
            logger.warning(f"  Slide {sid} ({title}): {fname}")
        logger.warning(
            "Generate with: python tools/kokoro_batch_generate.py\n"
            "  Or export texts: python tools/kokoro_batch_generate.py --export-text"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("DexIQ AI Presenter starting up...")
    _load_audience_config()
    logger.info(f"Loaded {len(_audience_config)} audience members.")
    _validate_audio_files()
    if tts_is_configured():
        logger.info("ElevenLabs TTS configured and ready for live responses.")
    else:
        logger.warning("ElevenLabs TTS NOT configured. Live responses will use text fallback.")
    yield
    logger.info("DexIQ AI Presenter shutting down.")


# --- FastAPI App ---
app = FastAPI(
    title="DexIQ AI Presenter",
    description="AI-powered presentation system with puppeteer control",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(presenter.router)
app.include_router(control.router)
app.include_router(audience.router)
app.include_router(tts.router)

# Serve static frontend files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/audio", StaticFiles(directory=str(frontend_path / "audio")), name="audio")
    app.mount("/css", StaticFiles(directory=str(frontend_path / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(frontend_path / "js")), name="js")
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# --- Health & Status Endpoints ---

@app.get("/")
async def root():
    return {"status": "ok", "app": "DexIQ AI Presenter", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "presenter_connections": presenter.get_presenter_count(),
        "control_connections": control.get_control_count(),
        "agent_state": presentation_state.get("agent_state", "unknown"),
        "current_slide": presentation_state.get("current_slide", 0),
        "queue_size": command_queue.queue_size,
    }


@app.get("/status")
async def status():
    return {
        "agent_state": presentation_state.get("agent_state", "unknown"),
        "current_slide": presentation_state.get("current_slide", 0),
        "total_slides": presentation_state.get("total_slides", 11),
        "is_audio_playing": presentation_state.get("is_audio_playing", False),
        "current_target": presentation_state.get("current_target"),
        "queue": command_queue.get_status(),
        "questions": {
            "total": question_manager.total_questions,
            "pending": question_manager.pending_count,
            "approved": question_manager.approved_count,
        },
    }


# --- Command Processing ---

async def handle_command(raw_text: str) -> dict:
    """Parse and process a command from the control interface.

    Args:
        raw_text: Raw command text (e.g., "/next", "/ask Maria: question", free text).

    Returns:
        Result dict with status and details.
    """
    global presentation_state, _pending_queued_command, _active_playback_token

    command = parse_command(raw_text)

    if command.type == "unknown" or command.type == "error":
        return {"status": "error", "message": command.payload.get("error", "Unknown command")}

    # Handle /status separately — it's informational, not queued
    if command.type == "status":
        return await status()

    # Handle /pause interrupt
    if command.type == "pause":
        previous = presentation_state.get("agent_state", AgentState.IDLE)
        presentation_state["previous_state"] = previous
        presentation_state["agent_state"] = AgentState.PAUSED
        presentation_state["is_audio_playing"] = False
        await presenter.broadcast_to_presenters({
            "type": "pause",
            "data": {"message": "Presentation paused."},
        })
        await control.send_to_control({
            "type": "status_update",
            "data": {"state": "paused", "message": f"Paused from {previous}. Type /resume to continue."},
        })
        return {"status": "paused", "previous_state": str(previous)}

    # Handle /skip — stop current audio, clear queued command, go idle
    if command.type == "skip":
        _pending_queued_command = None
        _active_playback_token = None
        presentation_state["is_audio_playing"] = False
        presentation_state["agent_state"] = AgentState.IDLE
        await presenter.broadcast_to_presenters({
            "type": "stop_audio",
            "data": {"message": "Skipped."},
        })
        await presenter.broadcast_to_presenters({"type": "show_avatar", "data": {"mode": "idle"}})
        await control.send_to_control({
            "type": "status_update",
            "data": {"state": "idle", "message": "Skipped. Ready for next command."},
        })
        return {"status": "ok", "command": "skip", "message": "Skipped current action."}

    # Handle /resume
    if command.type == "resume":
        previous = presentation_state.get("previous_state", AgentState.IDLE)
        presentation_state["agent_state"] = previous if previous else AgentState.IDLE
        await control.send_to_control({
            "type": "status_update",
            "data": {"state": str(previous), "message": f"Resumed to {previous}."},
        })
        return {"status": "resumed", "state": str(previous)}

    # Handle free-text answer during WAITING_ANSWER state
    if command.type == "answer":
        current_state = presentation_state.get("agent_state")
        if current_state not in (AgentState.WAITING_ANSWER, AgentState.ASKING):
            # If not waiting for an answer, treat as a general note
            logger.info(f"Free text received outside WAITING_ANSWER: {raw_text}")
            return {"status": "noted", "message": "Not currently waiting for an answer. Text noted."}

        # Process the answer through the live response pipeline
        return await _process_audience_response(command.payload.get("summary", ""))

    # Handle /pick N — answer a Q&A question live
    if command.type == "pick":
        return await _process_qa_pick(command.payload.get("question_id"))

    # Auto-fill question from slide config when /ask Name is used without a question
    if command.type == "ask" and not command.payload.get("question"):
        slide = presentation_state.get("current_slide", 0)
        config = _load_presentation_config()
        slides = config.get("slides", [])
        slide_config = next((s for s in slides if s.get("id") == slide), None)
        if slide_config and slide_config.get("interaction"):
            command.payload["question"] = slide_config["interaction"].get("question", "")
        if not command.payload.get("question"):
            return {
                "status": "error",
                "message": f"No interaction question configured for slide {slide}. "
                           f"Use /ask Name: Your question here",
            }

    # Queue command if audio is still playing — it will auto-execute when audio finishes
    if presentation_state.get("is_audio_playing") and command.type in ("next", "prev", "goto", "start", "ask"):
        _pending_queued_command = {"type": command.type, "payload": command.payload, "raw_text": raw_text}
        logger.info(f"Queued command '{command.type}' — will execute when audio finishes.")
        await control.send_to_control({
            "type": "status_update",
            "data": {
                "state": str(presentation_state.get("agent_state", "")),
                "message": f"Queued /{command.type} — will run when current audio finishes. Use /skip to interrupt.",
            },
        })
        return {"status": "queued", "command": command.type, "message": "Will execute when audio finishes."}

    # Execute the command immediately
    presentation_state["pending_command"] = {"type": command.type, "payload": command.payload}
    result = await _run_graph()

    return {"status": "ok", "command": command.type, **result}


async def _run_graph() -> dict:
    """Run the LangGraph state machine with the current state."""
    global presentation_state, _active_playback_token

    try:
        result = await asyncio.to_thread(
            presentation_graph.invoke, dict(presentation_state)
        )

        # Update global state with graph output
        for key, value in result.items():
            if key in presentation_state:
                presentation_state[key] = value

        # Send WebSocket messages to presenter screen
        ws_messages = result.get("ws_messages", [])
        for msg in ws_messages:
            if msg.get("type") == "play_audio":
                playback_token = uuid.uuid4().hex
                _active_playback_token = playback_token
                msg.setdefault("data", {})["playbackToken"] = playback_token
            await presenter.broadcast_to_presenters(msg)

        # Send status update to control interface
        agent_state = result.get("agent_state", "unknown")
        await control.send_to_control({
            "type": "status_update",
            "data": {"state": str(agent_state), "slide": result.get("current_slide", 0)},
        })

        # If we entered ASKING state, auto-transition to WAITING_ANSWER after audio
        if agent_state == AgentState.ASKING:
            presentation_state["agent_state"] = AgentState.WAITING_ANSWER

        return {"state": str(agent_state), "slide": result.get("current_slide", 0)}

    except Exception as e:
        logger.error(f"Graph execution error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


async def _process_audience_response(answer_summary: str) -> dict:
    """Process an audience member's answer and generate a live AI response.

    Pipeline: answer summary → Claude API → ElevenLabs TTS → presenter screen.
    """
    global presentation_state, _active_playback_token

    target = presentation_state.get("current_target", "someone")
    question = presentation_state.get("current_question", "")

    # Look up audience member role
    audience = _load_audience_config()
    member = audience.get(target.lower(), {})
    target_role = member.get("role", "team member")

    # Update state
    presentation_state["agent_state"] = AgentState.RESPONDING
    presentation_state["last_answer_summary"] = answer_summary

    # Show thinking animation
    await presenter.broadcast_to_presenters({
        "type": "show_avatar",
        "data": {"mode": "thinking"},
    })
    await control.send_to_control({
        "type": "status_update",
        "data": {"state": "responding", "message": f"Generating response to {target}..."},
    })

    try:
        # Generate response via LLM
        response_text = await generate_audience_response(
            target_name=target,
            target_role=target_role,
            question=question,
            answer_summary=answer_summary,
        )

        presentation_state["last_response"] = response_text
        logger.info(f"LLM response for {target}: {response_text[:200]}")

        # Send response text to control immediately so Chainlit shows it
        await control.send_to_control({
            "type": "response_generated",
            "data": {"target": target, "response": response_text},
        })

        # Stream live TTS audio to presenter in chunks
        if tts_is_configured():
            presentation_state["is_audio_playing"] = True
            presentation_state["current_audio_type"] = "live_tts"

            # Signal presenter to prepare for streaming audio
            playback_token = uuid.uuid4().hex
            _active_playback_token = playback_token
            await presenter.broadcast_to_presenters({
                "type": "stream_audio_start",
                "data": {"responseText": response_text, "playbackToken": playback_token},
            })
            await presenter.broadcast_to_presenters({
                "type": "show_avatar",
                "data": {"mode": "speaking_live"},
            })

            # Stream audio chunks to presenter
            async for chunk_msg in stream_speech_as_base64(response_text):
                await presenter.broadcast_to_presenters(chunk_msg)
        else:
            # No TTS configured — show text only
            logger.warning("ElevenLabs not configured. Showing response text only.")
            await presenter.broadcast_to_presenters({
                "type": "show_response_text",
                "data": {"text": response_text, "target": target},
            })

        return {"status": "ok", "response": response_text}

    except Exception as e:
        logger.error(f"Error generating audience response: {e}", exc_info=True)
        # Fallback: display text on screen without audio
        fallback = f"Thank you for sharing that, {target}. That's a great perspective."
        await presenter.broadcast_to_presenters({
            "type": "show_response_text",
            "data": {"text": fallback, "target": target},
        })
        return {"status": "fallback", "response": fallback, "error": str(e)}


async def _process_qa_pick(question_id: int) -> dict:
    """Process a /pick N command — answer a Q&A question live.

    Pipeline: fetch question → Claude API → ElevenLabs TTS → stream to presenter.
    """
    global presentation_state, _active_playback_token

    if question_id is None:
        return {"status": "error", "message": "/pick requires a question ID."}

    # Fetch the question
    question = question_manager.pick_question(question_id)
    if not question:
        return {"status": "error", "message": f"Question #{question_id} not found or already answered."}

    submitter = question.name or "Anonymous"
    logger.info(f"Answering Q&A question #{question_id} from {submitter}: {question.question}")

    # Update state
    presentation_state["agent_state"] = AgentState.RESPONDING
    presentation_state["current_qa_question_id"] = question_id

    # Show thinking animation
    await presenter.broadcast_to_presenters({
        "type": "show_avatar",
        "data": {"mode": "thinking"},
    })
    await presenter.broadcast_to_presenters({
        "type": "show_question",
        "data": {"targetName": submitter, "question": question.question},
    })
    await control.send_to_control({
        "type": "status_update",
        "data": {"state": "responding", "message": f"Answering #{question_id} from {submitter}..."},
    })

    try:
        # Generate answer via LLM
        answer_text = await generate_qa_answer(question.question)

        # Mark question as answered
        question_manager.mark_answered(question_id, answer_text)

        # Send answer to control immediately so Chainlit shows the text
        await control.send_to_control({
            "type": "response_generated",
            "data": {"target": submitter, "response": answer_text, "question_id": question_id},
        })

        # Stream live TTS audio to presenter
        if tts_is_configured():
            presentation_state["is_audio_playing"] = True
            presentation_state["current_audio_type"] = "live_tts"
            playback_token = uuid.uuid4().hex
            _active_playback_token = playback_token

            await presenter.broadcast_to_presenters({
                "type": "stream_audio_start",
                "data": {"responseText": answer_text, "playbackToken": playback_token},
            })
            await presenter.broadcast_to_presenters({
                "type": "show_avatar",
                "data": {"mode": "speaking_live"},
            })

            async for chunk_msg in stream_speech_as_base64(answer_text):
                await presenter.broadcast_to_presenters(chunk_msg)
        else:
            logger.warning("ElevenLabs not configured. Showing answer text only.")
            await presenter.broadcast_to_presenters({
                "type": "show_response_text",
                "data": {"text": answer_text, "target": submitter},
            })

        return {"status": "ok", "answer": answer_text, "question_id": question_id}

    except Exception as e:
        logger.error(f"Error answering Q&A question #{question_id}: {e}", exc_info=True)
        fallback = "That's a great question. I'd recommend exploring the tools we discussed today to find the best fit."
        await presenter.broadcast_to_presenters({
            "type": "show_response_text",
            "data": {"text": fallback, "target": submitter},
        })
        return {"status": "fallback", "answer": fallback, "error": str(e)}


async def handle_audio_complete(playback_token: str | None = None):
    """Called when the presenter screen reports audio playback finished."""
    global presentation_state, _active_playback_token

    if _active_playback_token:
        if playback_token != _active_playback_token:
            logger.info(
                "Ignoring stale audio_ended event (token=%s, active=%s)",
                playback_token,
                _active_playback_token,
            )
            return

    _active_playback_token = None

    presentation_state["is_audio_playing"] = False

    current_state = presentation_state.get("agent_state")

    # After asking audio finishes, transition to waiting for answer
    if current_state == AgentState.ASKING:
        presentation_state["agent_state"] = AgentState.WAITING_ANSWER
        await control.send_to_control({
            "type": "status_update",
            "data": {
                "state": "waiting_answer",
                "message": f"Waiting for {presentation_state.get('current_target', 'someone')}'s answer...",
            },
        })

    # After responding finishes, return to QA_MODE if we were answering a Q&A question,
    # otherwise go back to IDLE
    elif current_state == AgentState.RESPONDING:
        if presentation_state.get("current_qa_question_id") is not None:
            presentation_state["agent_state"] = AgentState.QA_MODE
            presentation_state["current_qa_question_id"] = None
            await presenter.broadcast_to_presenters({"type": "show_avatar", "data": {"mode": "idle"}})
            await control.send_to_control({
                "type": "status_update",
                "data": {"state": "qa_mode", "message": "Ready for next question. Use /pick N or /outro."},
            })
        else:
            presentation_state["agent_state"] = AgentState.IDLE
            await presenter.broadcast_to_presenters({"type": "show_avatar", "data": {"mode": "idle"}})
            await control.send_to_control({
                "type": "status_update",
                "data": {"state": "idle", "message": "Response complete. Ready for next command."},
            })

    # After outro finishes, mark as done
    elif current_state == AgentState.OUTRO:
        presentation_state["agent_state"] = AgentState.DONE
        await control.send_to_control({
            "type": "status_update",
            "data": {"state": "done", "message": "Presentation complete!"},
        })

    logger.info(f"Audio complete. State: {presentation_state.get('agent_state')}")

    # Auto-execute any queued command
    await _process_queued_command()


async def _process_queued_command():
    """Execute a pending queued command if one exists."""
    global _pending_queued_command, presentation_state

    if _pending_queued_command is None:
        return

    queued = _pending_queued_command
    _pending_queued_command = None

    logger.info(f"Auto-executing queued command: {queued['type']}")
    try:
        result = await handle_command(queued.get("raw_text", f"/{queued['type']}"))
        logger.info(f"Queued command result: {result}")
    except Exception as e:
        logger.error(f"Error executing queued command: {e}", exc_info=True)


async def filter_and_queue_question(question_id: int):
    """Filter a submitted question using the LLM and update its status."""
    question = question_manager.get_question(question_id)
    if not question:
        return

    try:
        result = await llm_filter_question(question.question)
        from backend.models.questions import QuestionFilterResult
        filter_result = QuestionFilterResult(**result)
        question_manager.apply_filter_result(question_id, filter_result)

        # Notify control interface about new question
        await control.send_to_control({
            "type": "new_question",
            "data": {
                "id": question.id,
                "name": question.name or "Anonymous",
                "question": question.question,
                "score": result.get("score", 0),
                "flag": result.get("flag"),
            },
        })
    except Exception as e:
        logger.error(f"Error filtering question #{question_id}: {e}")


# --- Entry point for uvicorn ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
