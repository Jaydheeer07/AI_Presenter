"""Action executors for each agent state.

Each function corresponds to a LangGraph node and performs the actual work
for that state: playing audio, calling LLM, advancing slides, etc.
"""

import logging
from typing import Any

from backend.agent.states import GraphState
from backend.models.presentation import AgentState, AudioType

logger = logging.getLogger(__name__)


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
        {"type": "play_audio", "data": {"audioUrl": "/audio/slide_01_intro.mp3", "audioType": "pre_generated"}},
        {"type": "status", "data": {"state": "introducing", "message": "DexIQ is introducing itself..."}},
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

    audio_map = {
        2: "slide_02_why.mp3",
        3: "slide_03_what_ai_is.mp3",
        4: "slide_04_chatgpt.mp3",
        5: "slide_05_ecosystem.mp3",
        6: "slide_06_advanced.mp3",
        7: "slide_07_entertainment.mp3",
        8: "slide_08_safety.mp3",
        9: "slide_09_qa.mp3",
        10: "slide_10_outro.mp3",
    }

    audio_file = audio_map.get(slide, f"slide_{slide:02d}.mp3")

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
    logger.info(f"Asking {target}: {question}")

    ws_messages = [
        {"type": "show_question", "data": {"question": question, "targetName": target}},
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {"type": "play_audio", "data": {
            "audioUrl": f"/audio/ask_{target.lower()}.mp3",
            "audioType": "pre_generated",
            "fallback": True,
        }},
        {"type": "status", "data": {"state": "asking", "target": target, "question": question}},
    ]

    return {
        "agent_state": AgentState.ASKING,
        "is_audio_playing": True,
        "current_audio_type": AudioType.PRE_GENERATED,
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
        {"type": "goto_slide", "data": {"slideIndex": 9}},
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {"type": "play_audio", "data": {"audioUrl": "/audio/slide_09_qa.mp3", "audioType": "pre_generated"}},
        {"type": "status", "data": {"state": "qa_mode", "message": "Q&A mode active. Use /pick N to answer questions."}},
    ]

    return {
        "agent_state": AgentState.QA_MODE,
        "current_slide": 9,
        "is_audio_playing": True,
        "current_audio_type": AudioType.PRE_GENERATED,
        "ws_messages": ws_messages,
    }


def outro_node(state: GraphState) -> dict:
    """OUTRO state — AI delivers closing remarks."""
    logger.info("Delivering outro.")

    ws_messages = [
        {"type": "goto_slide", "data": {"slideIndex": 10}},
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {"type": "play_audio", "data": {"audioUrl": "/audio/slide_10_outro.mp3", "audioType": "pre_generated"}},
        {"type": "status", "data": {"state": "outro", "message": "DexIQ is delivering closing remarks..."}},
    ]

    return {
        "agent_state": AgentState.OUTRO,
        "current_slide": 10,
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
