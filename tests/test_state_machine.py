"""Tests for the LangGraph state machine.

These tests validate the routing logic and state transitions
without requiring the full langgraph dependency.
"""

import pytest

from backend.models.presentation import AgentState, AudioType


def create_initial_state(total_slides: int = 11) -> dict:
    """Create a test-friendly initial state dict (no langgraph dependency)."""
    return {
        "agent_state": AgentState.IDLE,
        "previous_state": None,
        "current_slide": 0,
        "total_slides": total_slides,
        "is_audio_playing": False,
        "current_audio_type": AudioType.NONE,
        "current_target": None,
        "current_target_role": None,
        "current_question": None,
        "last_answer_summary": None,
        "last_response": None,
        "qa_questions_answered": 0,
        "current_qa_question": None,
        "current_qa_question_id": None,
        "pending_command": None,
        "messages": [],
        "last_error": None,
        "ws_messages": [],
    }


# Import actions after defining the test helper to avoid langgraph import at module level
try:
    from backend.agent.actions import decide_next_state, route_next_command
except ImportError:
    # If langgraph is not installed, define minimal stubs for the routing functions
    # that mirror the logic in actions.py without the langgraph type hints
    import importlib
    import sys
    from unittest.mock import MagicMock

    # Mock langgraph so the import chain works
    langgraph_mock = MagicMock()
    sys.modules["langgraph"] = langgraph_mock
    sys.modules["langgraph.graph"] = langgraph_mock
    langgraph_mock.add_messages = lambda x, y: x + y

    from backend.agent.actions import decide_next_state, route_next_command


class TestInitialState:
    """Test initial state creation."""

    def test_default_state(self):
        state = create_initial_state()
        assert state["agent_state"] == AgentState.IDLE
        assert state["current_slide"] == 0
        assert state["total_slides"] == 11
        assert state["is_audio_playing"] is False
        assert state["pending_command"] is None

    def test_custom_total_slides(self):
        state = create_initial_state(total_slides=5)
        assert state["total_slides"] == 5


class TestRouteNextCommand:
    """Test the router node that decides the next state."""

    def test_no_pending_command(self):
        state = create_initial_state()
        result = route_next_command(state)
        assert result["agent_state"] == AgentState.IDLE

    def test_intro_command(self):
        state = create_initial_state()
        state["pending_command"] = {"type": "intro", "payload": {}}
        result = route_next_command(state)
        assert result["agent_state"] == AgentState.INTRODUCING

    def test_start_command(self):
        state = create_initial_state()
        state["pending_command"] = {"type": "start", "payload": {}}
        result = route_next_command(state)
        assert result["agent_state"] == AgentState.PRESENTING
        assert result["current_slide"] == 2

    def test_next_command(self):
        state = create_initial_state()
        state["current_slide"] = 3
        state["pending_command"] = {"type": "next", "payload": {}}
        result = route_next_command(state)
        assert result["agent_state"] == AgentState.PRESENTING
        assert result["current_slide"] == 4

    def test_next_at_last_slide(self):
        state = create_initial_state()
        state["current_slide"] = 10
        state["pending_command"] = {"type": "next", "payload": {}}
        result = route_next_command(state)
        assert result["current_slide"] == 10  # Clamped to max

    def test_prev_command(self):
        state = create_initial_state()
        state["current_slide"] = 5
        state["pending_command"] = {"type": "prev", "payload": {}}
        result = route_next_command(state)
        assert result["current_slide"] == 4

    def test_prev_at_first_slide(self):
        state = create_initial_state()
        state["current_slide"] = 0
        state["pending_command"] = {"type": "prev", "payload": {}}
        result = route_next_command(state)
        assert result["current_slide"] == 0  # Clamped to 0

    def test_goto_command(self):
        state = create_initial_state()
        state["pending_command"] = {"type": "goto", "payload": {"slide_number": 7}}
        result = route_next_command(state)
        assert result["current_slide"] == 7

    def test_goto_clamped(self):
        state = create_initial_state()
        state["pending_command"] = {"type": "goto", "payload": {"slide_number": 99}}
        result = route_next_command(state)
        assert result["current_slide"] == 10  # Clamped to total_slides - 1

    def test_ask_command(self):
        state = create_initial_state()
        state["pending_command"] = {
            "type": "ask",
            "payload": {"target_name": "Maria", "question": "What tools do you use?"},
        }
        result = route_next_command(state)
        assert result["agent_state"] == AgentState.ASKING
        assert result["current_target"] == "Maria"
        assert result["current_question"] == "What tools do you use?"

    def test_answer_command(self):
        state = create_initial_state()
        state["pending_command"] = {
            "type": "answer",
            "payload": {"summary": "She uses ChatGPT for emails"},
        }
        result = route_next_command(state)
        assert result["agent_state"] == AgentState.RESPONDING
        assert result["last_answer_summary"] == "She uses ChatGPT for emails"

    def test_qa_command(self):
        state = create_initial_state()
        state["pending_command"] = {"type": "qa", "payload": {}}
        result = route_next_command(state)
        assert result["agent_state"] == AgentState.QA_MODE

    def test_outro_command(self):
        state = create_initial_state()
        state["pending_command"] = {"type": "outro", "payload": {}}
        result = route_next_command(state)
        assert result["agent_state"] == AgentState.OUTRO

    def test_skip_command(self):
        state = create_initial_state()
        state["agent_state"] = AgentState.PRESENTING
        state["pending_command"] = {"type": "skip", "payload": {}}
        result = route_next_command(state)
        assert result["agent_state"] == AgentState.IDLE

    def test_resume_command(self):
        state = create_initial_state()
        state["previous_state"] = AgentState.PRESENTING
        state["pending_command"] = {"type": "resume", "payload": {}}
        result = route_next_command(state)
        assert result["agent_state"] == AgentState.PRESENTING


class TestDecideNextState:
    """Test the conditional edge function."""

    def test_all_states_mapped(self):
        for agent_state in AgentState:
            state = create_initial_state()
            state["agent_state"] = agent_state
            result = decide_next_state(state)
            assert isinstance(result, str)

    def test_done_goes_to_end(self):
        state = create_initial_state()
        state["agent_state"] = AgentState.DONE
        assert decide_next_state(state) == "__end__"

    def test_idle_goes_to_idle(self):
        state = create_initial_state()
        state["agent_state"] = AgentState.IDLE
        assert decide_next_state(state) == "idle"
