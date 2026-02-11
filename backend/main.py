"""FastAPI application entry point for the DexIQ AI Presenter.

Orchestrates the presentation: receives commands from Chainlit,
processes them through the LangGraph state machine, and sends
actions to the presenter screen via WebSocket.
"""

import asyncio
import logging
import os
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
from backend.routers import audience, control, presenter
from backend.services.llm_service import (
    filter_question as llm_filter_question,
    generate_audience_response,
    generate_qa_answer,
)
from backend.services.question_manager import QuestionManager
from backend.services.tts_service import synthesize_speech

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

# Audience config cache
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("DexIQ AI Presenter starting up...")
    _load_audience_config()
    logger.info(f"Loaded {len(_audience_config)} audience members.")
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
    global presentation_state

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

    # Queue the command for processing
    presentation_state["pending_command"] = {"type": command.type, "payload": command.payload}
    result = await _run_graph()

    return {"status": "ok", "command": command.type, **result}


async def _run_graph() -> dict:
    """Run the LangGraph state machine with the current state."""
    global presentation_state

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
    global presentation_state

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

        # Generate live TTS audio
        audio_bytes = await synthesize_speech(response_text)

        # Send audio to presenter screen as base64
        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        await presenter.broadcast_to_presenters({
            "type": "play_live_audio",
            "data": {
                "audioData": audio_b64,
                "audioType": "live",
                "responseText": response_text,
            },
        })
        await presenter.broadcast_to_presenters({
            "type": "show_avatar",
            "data": {"mode": "speaking"},
        })

        # Send response text to control
        await control.send_to_control({
            "type": "response_generated",
            "data": {"target": target, "response": response_text},
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


async def handle_audio_complete():
    """Called when the presenter screen reports audio playback finished."""
    global presentation_state

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

    # After responding finishes, go back to idle (ready for next command)
    elif current_state == AgentState.RESPONDING:
        presentation_state["agent_state"] = AgentState.IDLE
        await presenter.broadcast_to_presenters({"type": "show_avatar", "data": {"mode": "idle"}})

    # After outro finishes, mark as done
    elif current_state == AgentState.OUTRO:
        presentation_state["agent_state"] = AgentState.DONE
        await control.send_to_control({
            "type": "status_update",
            "data": {"state": "done", "message": "Presentation complete!"},
        })

    logger.info(f"Audio complete. State: {presentation_state.get('agent_state')}")


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
