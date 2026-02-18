"""State definitions and typed dict for LangGraph state machine."""

from typing import Annotated, Any, Optional

from langgraph.graph import add_messages
from typing_extensions import TypedDict

from backend.models.presentation import AgentState, AudioType


class GraphState(TypedDict):
    """The state that flows through the LangGraph state machine.

    This is the canonical state representation used by LangGraph nodes.
    Each node reads from and writes to this state.
    """
    # Core state
    agent_state: AgentState
    previous_state: Optional[AgentState]

    # Slide tracking
    current_slide: int
    total_slides: int

    # Audio state
    is_audio_playing: bool
    current_audio_type: AudioType

    # Audience interaction
    current_target: Optional[str]
    current_target_role: Optional[str]
    current_question: Optional[str]
    last_answer_summary: Optional[str]
    last_response: Optional[str]

    # Q&A
    qa_questions_answered: int
    current_qa_question: Optional[str]
    current_qa_question_id: Optional[int]

    # Command context
    pending_command: Optional[dict]

    # Conversation history (for LLM context)
    messages: Annotated[list, add_messages]

    # Error tracking
    last_error: Optional[str]

    # WebSocket messages to send
    ws_messages: list[dict]


def create_initial_state(total_slides: int = 15) -> GraphState:
    """Create the initial state for a new presentation."""
    return GraphState(
        agent_state=AgentState.IDLE,
        previous_state=None,
        current_slide=0,
        total_slides=total_slides,
        is_audio_playing=False,
        current_audio_type=AudioType.NONE,
        current_target=None,
        current_target_role=None,
        current_question=None,
        last_answer_summary=None,
        last_response=None,
        qa_questions_answered=0,
        current_qa_question=None,
        current_qa_question_id=None,
        pending_command=None,
        messages=[],
        last_error=None,
        ws_messages=[],
    )
