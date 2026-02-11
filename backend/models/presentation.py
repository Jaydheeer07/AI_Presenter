"""Pydantic models for presentation configuration and state."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """All possible states of the presentation agent."""
    IDLE = "idle"
    INTRODUCING = "introducing"
    PRESENTING = "presenting"
    ASKING = "asking"
    WAITING_ANSWER = "waiting_answer"
    RESPONDING = "responding"
    TRANSITIONING = "transitioning"
    QA_MODE = "qa_mode"
    OUTRO = "outro"
    PAUSED = "paused"
    DONE = "done"


class AudioType(str, Enum):
    """Type of audio being played."""
    PRE_GENERATED = "pre_generated"
    LIVE = "live"
    NONE = "none"


class SlideInteraction(BaseModel):
    """Configuration for an audience interaction on a slide."""
    target: str = "TBD"
    question: str
    question_audio: Optional[str] = None
    fallback_response: str = ""


class SlideConfig(BaseModel):
    """Configuration for a single slide."""
    id: int
    title: str
    narration: Optional[str] = None
    audio_file: Optional[str] = None
    has_interaction: bool = False
    interaction: Optional[SlideInteraction] = None
    trigger: Optional[str] = None
    notes: Optional[str] = None


class PresentationConfig(BaseModel):
    """Top-level presentation configuration."""
    title: str
    presenter_name: str = "DexIQ"
    presenter_description: str = ""
    total_slides: int = 11


class AudienceMember(BaseModel):
    """Configuration for an audience member."""
    name: str
    role: str = ""
    slide_interaction: Optional[int] = None
    question: str = ""
    question_audio: Optional[str] = None


class PresentationState(BaseModel):
    """The full runtime state of the presentation."""
    agent_state: AgentState = AgentState.IDLE
    previous_state: Optional[AgentState] = None
    current_slide: int = 0
    total_slides: int = 11
    is_audio_playing: bool = False
    current_audio_type: AudioType = AudioType.NONE

    # Audience interaction context
    current_target: Optional[str] = None
    current_question: Optional[str] = None
    last_answer_summary: Optional[str] = None
    last_response: Optional[str] = None

    # Q&A context
    qa_questions_answered: int = 0

    # Conversation history for LLM context
    conversation_history: list[dict] = Field(default_factory=list)


class WebSocketMessage(BaseModel):
    """Message sent over WebSocket to the presenter screen."""
    type: str
    data: dict = Field(default_factory=dict)


class ControlMessage(BaseModel):
    """Message received from the Chainlit control interface."""
    type: str
    payload: dict = Field(default_factory=dict)
