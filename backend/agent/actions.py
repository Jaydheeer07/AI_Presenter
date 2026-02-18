"""Action executors for each agent state.

Each function corresponds to a LangGraph node and performs the actual work
for that state: playing audio, calling LLM, advancing slides, etc.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from backend.agent.states import GraphState
from backend.models.presentation import AgentState, AudioType

logger = logging.getLogger(__name__)

def _get_audio_file(slide: int) -> str:
    """Get the audio filename for a given slide index."""
    slide_audio_map = _load_slide_audio_map()
    return slide_audio_map.get(slide, f"slide_{slide:02d}.mp3")


@lru_cache(maxsize=1)
def _load_slide_audio_map() -> dict[int, str]:
    """Load per-slide narration audio mapping from config/presentation.yaml."""
    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "presentation.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"Presentation config not found at {config_path}")
        return {}
    except Exception as e:
        logger.warning(f"Failed to load slide audio map from {config_path}: {e}")
        return {}

    mapping: dict[int, str] = {}
    for slide in data.get("slides", []):
        slide_id = slide.get("id")
        audio_file = slide.get("audio_file")
        if isinstance(slide_id, int) and audio_file:
            mapping[slide_id] = Path(audio_file).name

    return mapping


@lru_cache(maxsize=1)
def _load_question_audio_map() -> dict[int, str]:
    """Load per-slide question audio mapping from config/presentation.yaml."""
    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "presentation.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"Presentation config not found at {config_path}")
        return {}
    except Exception as e:
        logger.warning(f"Failed to load question audio map from {config_path}: {e}")
        return {}

    mapping: dict[int, str] = {}
    for slide in data.get("slides", []):
        slide_id = slide.get("id")
        interaction = slide.get("interaction") or {}
        question_audio = interaction.get("question_audio")
        if isinstance(slide_id, int) and question_audio:
            mapping[slide_id] = Path(question_audio).name

    return mapping


def idle_node(state: GraphState) -> dict:
    """IDLE state — waiting for the first command."""
    logger.info("Agent is idle, waiting for commands.")
    return {
        "agent_state": AgentState.IDLE,
        "ws_messages": [{"type": "status", "data": {"state": "idle", "message": "Waiting for commands..."}}],
    }


def introducing_node(state: GraphState) -> dict:
    """INTRODUCING state — AI delivers its introduction."""
    logger.info("Starting introduction.")
    slide_index = 1

    ws_messages = [
        {"type": "goto_slide", "data": {"slideIndex": slide_index}},
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {"type": "play_audio", "data": {"audioUrl": f"/audio/{_get_audio_file(slide_index)}", "audioType": "pre_generated"}},
        {"type": "status", "data": {"state": "introducing", "message": "ARIA is introducing itself..."}},
    ]

    return {
        "agent_state": AgentState.INTRODUCING,
        "current_slide": slide_index,
        "is_audio_playing": True,
        "current_audio_type": AudioType.PRE_GENERATED,
        "ws_messages": ws_messages,
    }


def presenting_node(state: GraphState) -> dict:
    """PRESENTING state — narrating the current slide with pre-generated audio."""
    slide = state["current_slide"]
    logger.info(f"Presenting slide {slide}.")

    audio_file = _get_audio_file(slide)

    ws_messages = [
        {"type": "goto_slide", "data": {"slideIndex": slide}},
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {"type": "play_audio", "data": {"audioUrl": f"/audio/{audio_file}", "audioType": "pre_generated"}},
        {"type": "status", "data": {"state": "presenting", "slide": slide}},
    ]

    return {
        "agent_state": AgentState.PRESENTING,
        "is_audio_playing": True,
        "current_audio_type": AudioType.PRE_GENERATED,
        "ws_messages": ws_messages,
    }


def asking_node(state: GraphState) -> dict:
    """ASKING state — AI asks a specific audience member a question."""
    target = state.get("current_target", "someone")
    question = state.get("current_question", "")
    slide = state.get("current_slide", 0)
    logger.info(f"Asking {target}: {question}")

    # Use question audio from config to avoid stale hardcoded filenames.
    question_audio_map = _load_question_audio_map()
    audio_file = question_audio_map.get(slide)

    ws_messages = [
        {"type": "show_question", "data": {"question": question, "targetName": target}},
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {"type": "status", "data": {"state": "asking", "target": target, "question": question}},
    ]

    is_audio_playing = False
    current_audio_type = AudioType.NONE
    if audio_file:
        ws_messages.insert(2, {"type": "play_audio", "data": {
            "audioUrl": f"/audio/{audio_file}",
            "audioType": "pre_generated",
            "fallback": True,
        }})
        is_audio_playing = True
        current_audio_type = AudioType.PRE_GENERATED
    else:
        logger.warning(f"No configured question audio for slide {slide}; asking without pre-generated audio.")

    return {
        "agent_state": AgentState.ASKING,
        "is_audio_playing": is_audio_playing,
        "current_audio_type": current_audio_type,
        "ws_messages": ws_messages,
    }


def waiting_answer_node(state: GraphState) -> dict:
    """WAITING_ANSWER state — waiting for the puppeteer to type the answer summary."""
    target = state.get("current_target", "someone")
    logger.info(f"Waiting for {target}'s answer summary from puppeteer.")

    ws_messages = [
        {"type": "show_avatar", "data": {"mode": "listening"}},
        {"type": "status", "data": {
            "state": "waiting_answer",
            "message": f"Waiting for {target}'s answer... Type their response summary.",
        }},
    ]

    return {
        "agent_state": AgentState.WAITING_ANSWER,
        "is_audio_playing": False,
        "current_audio_type": AudioType.NONE,
        "ws_messages": ws_messages,
    }


def responding_node(state: GraphState) -> dict:
    """RESPONDING state — AI generates a live response to the audience member's answer.

    This node prepares the state for live LLM + TTS generation.
    The actual LLM call and TTS happen in the action executor service.
    """
    target = state.get("current_target", "someone")
    answer = state.get("last_answer_summary", "")
    logger.info(f"Generating response to {target}'s answer: {answer}")

    ws_messages = [
        {"type": "show_avatar", "data": {"mode": "thinking"}},
        {"type": "status", "data": {
            "state": "responding",
            "message": f"Generating response to {target}...",
        }},
    ]

    return {
        "agent_state": AgentState.RESPONDING,
        "is_audio_playing": False,
        "current_audio_type": AudioType.NONE,
        "ws_messages": ws_messages,
    }


def transitioning_node(state: GraphState) -> dict:
    """TRANSITIONING state — brief pause between states."""
    logger.info("Transitioning between states.")
    return {
        "agent_state": AgentState.TRANSITIONING,
        "is_audio_playing": False,
        "current_audio_type": AudioType.NONE,
        "ws_messages": [{"type": "show_avatar", "data": {"mode": "idle"}}],
    }


def qa_mode_node(state: GraphState) -> dict:
    """QA_MODE state — answering audience-submitted questions."""
    logger.info("Entering Q&A mode.")

    ws_messages = [
        {"type": "goto_slide", "data": {"slideIndex": 12}},
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {"type": "play_audio", "data": {"audioUrl": f"/audio/{_get_audio_file(12)}", "audioType": "pre_generated"}},
        {"type": "status", "data": {"state": "qa_mode", "message": "Q&A mode active. Use /pick N to answer questions."}},
    ]

    return {
        "agent_state": AgentState.QA_MODE,
        "current_slide": 12,
        "is_audio_playing": True,
        "current_audio_type": AudioType.PRE_GENERATED,
        "ws_messages": ws_messages,
    }


def outro_node(state: GraphState) -> dict:
    """OUTRO state — AI delivers closing remarks."""
    logger.info("Delivering outro.")

    ws_messages = [
        {"type": "goto_slide", "data": {"slideIndex": 14}},
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {"type": "play_audio", "data": {"audioUrl": f"/audio/{_get_audio_file(14)}", "audioType": "pre_generated"}},
        {"type": "status", "data": {"state": "outro", "message": "ARIA is delivering closing remarks..."}},
    ]

    return {
        "agent_state": AgentState.OUTRO,
        "current_slide": 14,
        "is_audio_playing": True,
        "current_audio_type": AudioType.PRE_GENERATED,
        "ws_messages": ws_messages,
    }


def route_next_command(state: GraphState) -> dict:
    """Router node — checks the pending command and decides the next state."""
    pending = state.get("pending_command")
    if not pending:
        logger.info("No pending command, staying idle.")
        return {"agent_state": AgentState.IDLE, "pending_command": None, "ws_messages": []}

    cmd_type = pending.get("type", "")
    payload = pending.get("payload", {})
    logger.info(f"Routing command: {cmd_type}")

    result: dict[str, Any] = {"pending_command": None, "ws_messages": []}

    if cmd_type == "intro":
        result["agent_state"] = AgentState.INTRODUCING

    elif cmd_type == "start":
        result["agent_state"] = AgentState.PRESENTING
        result["current_slide"] = 2

    elif cmd_type == "next":
        next_slide = min(state["current_slide"] + 1, state["total_slides"] - 1)
        result["agent_state"] = AgentState.PRESENTING
        result["current_slide"] = next_slide

    elif cmd_type == "prev":
        prev_slide = max(state["current_slide"] - 1, 0)
        result["agent_state"] = AgentState.PRESENTING
        result["current_slide"] = prev_slide

    elif cmd_type == "goto":
        slide_num = payload.get("slide_number", 0)
        slide_num = max(0, min(slide_num, state["total_slides"] - 1))
        result["agent_state"] = AgentState.PRESENTING
        result["current_slide"] = slide_num

    elif cmd_type == "ask":
        result["agent_state"] = AgentState.ASKING
        result["current_target"] = payload.get("target_name", "")
        result["current_question"] = payload.get("question", "")

    elif cmd_type == "answer":
        result["agent_state"] = AgentState.RESPONDING
        result["last_answer_summary"] = payload.get("summary", "")

    elif cmd_type == "example":
        result["agent_state"] = AgentState.RESPONDING
        result["last_answer_summary"] = "__example__"

    elif cmd_type == "qa":
        result["agent_state"] = AgentState.QA_MODE

    elif cmd_type == "pick":
        result["agent_state"] = AgentState.QA_MODE
        result["current_qa_question_id"] = payload.get("question_id")

    elif cmd_type == "outro":
        result["agent_state"] = AgentState.OUTRO

    elif cmd_type == "resume":
        prev = state.get("previous_state", AgentState.IDLE)
        result["agent_state"] = prev if prev else AgentState.IDLE

    elif cmd_type == "skip":
        result["agent_state"] = AgentState.IDLE

    else:
        result["agent_state"] = AgentState.IDLE

    return result


def decide_next_state(state: GraphState) -> str:
    """Conditional edge function — returns the name of the next node."""
    agent_state = state.get("agent_state", AgentState.IDLE)

    state_to_node = {
        AgentState.IDLE: "idle",
        AgentState.INTRODUCING: "introducing",
        AgentState.PRESENTING: "presenting",
        AgentState.ASKING: "asking",
        AgentState.WAITING_ANSWER: "waiting_answer",
        AgentState.RESPONDING: "responding",
        AgentState.TRANSITIONING: "transitioning",
        AgentState.QA_MODE: "qa_mode",
        AgentState.OUTRO: "outro",
        AgentState.DONE: "__end__",
    }

    return state_to_node.get(agent_state, "idle")
