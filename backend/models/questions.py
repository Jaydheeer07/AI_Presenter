"""Pydantic models for the audience Q&A system."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class QuestionStatus(str, Enum):
    """Status of a submitted question."""
    PENDING = "pending"
    APPROVED = "approved"
    ANSWERED = "answered"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class AudienceQuestion(BaseModel):
    """A question submitted by an audience member."""
    id: int = 0
    name: Optional[str] = None
    question: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    status: QuestionStatus = QuestionStatus.PENDING
    relevance_score: Optional[int] = None
    flag: Optional[str] = None
    flag_reason: Optional[str] = None
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None


class QuestionSubmission(BaseModel):
    """Incoming question submission from the audience Q&A page."""
    name: Optional[str] = None
    question: str


class QuestionFilterResult(BaseModel):
    """Result from the AI question filter."""
    score: int
    flag: Optional[str] = None
    reason: str = ""
