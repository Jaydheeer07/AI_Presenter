"""Question manager for the audience Q&A system.

Manages the question queue: receiving submissions, filtering, and selecting
questions for the AI to answer.
"""

import logging
from datetime import datetime
from typing import Optional

from backend.models.questions import AudienceQuestion, QuestionFilterResult, QuestionStatus

logger = logging.getLogger(__name__)


class QuestionManager:
    """Manages audience Q&A questions with filtering and selection."""

    def __init__(self):
        self._questions: list[AudienceQuestion] = []
        self._next_id: int = 1
        self._answered_questions: list[AudienceQuestion] = []

    @property
    def total_questions(self) -> int:
        return len(self._questions)

    @property
    def pending_count(self) -> int:
        return sum(1 for q in self._questions if q.status == QuestionStatus.PENDING)

    @property
    def approved_count(self) -> int:
        return sum(1 for q in self._questions if q.status == QuestionStatus.APPROVED)

    def submit_question(self, question: str, name: Optional[str] = None) -> AudienceQuestion:
        """Submit a new question from an audience member.

        Args:
            question: The question text.
            name: Optional name of the submitter.

        Returns:
            The created AudienceQuestion.
        """
        q = AudienceQuestion(
            id=self._next_id,
            name=name,
            question=question,
            submitted_at=datetime.utcnow(),
            status=QuestionStatus.PENDING,
        )
        self._next_id += 1
        self._questions.append(q)
        logger.info(f"Question #{q.id} submitted by {name or 'Anonymous'}: {question[:50]}...")
        return q

    def apply_filter_result(self, question_id: int, result: QuestionFilterResult):
        """Apply AI filter results to a question.

        Args:
            question_id: The question ID.
            result: The filter result with score and flag.
        """
        q = self.get_question(question_id)
        if not q:
            return

        q.relevance_score = result.score
        q.flag = result.flag
        q.flag_reason = result.reason

        if result.flag:
            q.status = QuestionStatus.FLAGGED
            logger.info(f"Question #{question_id} flagged: {result.flag} - {result.reason}")
        elif result.score >= 6:
            q.status = QuestionStatus.APPROVED
            logger.info(f"Question #{question_id} auto-approved (score: {result.score})")
        else:
            logger.info(f"Question #{question_id} scored {result.score}, remains pending.")

    def get_question(self, question_id: int) -> Optional[AudienceQuestion]:
        """Get a question by ID."""
        for q in self._questions:
            if q.id == question_id:
                return q
        return None

    def get_next_approved(self) -> Optional[AudienceQuestion]:
        """Get the next approved question to answer (FIFO order)."""
        for q in self._questions:
            if q.status == QuestionStatus.APPROVED:
                return q
        return None

    def pick_question(self, question_id: int) -> Optional[AudienceQuestion]:
        """Manually select a specific question to answer (by the puppeteer).

        Args:
            question_id: The question ID to pick.

        Returns:
            The selected question, or None if not found.
        """
        q = self.get_question(question_id)
        if q and q.status != QuestionStatus.ANSWERED:
            q.status = QuestionStatus.APPROVED
            return q
        return None

    def mark_answered(self, question_id: int, answer: str):
        """Mark a question as answered.

        Args:
            question_id: The question ID.
            answer: The generated answer text.
        """
        q = self.get_question(question_id)
        if q:
            q.status = QuestionStatus.ANSWERED
            q.answer = answer
            q.answered_at = datetime.utcnow()
            self._answered_questions.append(q)
            logger.info(f"Question #{question_id} answered.")

    def get_all_questions(self) -> list[dict]:
        """Get all questions as a list of dicts (for status display)."""
        return [
            {
                "id": q.id,
                "name": q.name or "Anonymous",
                "question": q.question,
                "status": q.status.value,
                "score": q.relevance_score,
                "flag": q.flag,
            }
            for q in self._questions
        ]

    def get_pending_questions(self) -> list[AudienceQuestion]:
        """Get all pending questions."""
        return [q for q in self._questions if q.status == QuestionStatus.PENDING]

    def get_approved_questions(self) -> list[AudienceQuestion]:
        """Get all approved questions."""
        return [q for q in self._questions if q.status == QuestionStatus.APPROVED]

    def clear(self):
        """Clear all questions."""
        self._questions.clear()
        self._answered_questions.clear()
        self._next_id = 1
