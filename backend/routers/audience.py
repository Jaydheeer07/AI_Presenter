"""REST endpoints for the audience Q&A system.

Audience members submit questions via a simple web form.
Questions are received here, filtered, and queued for the AI to answer.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.models.questions import QuestionSubmission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/questions", tags=["audience"])


@router.post("/submit")
async def submit_question(submission: QuestionSubmission):
    """Submit a question from an audience member.

    Called by the audience Q&A page (ask.html) when someone submits a question.
    """
    if not submission.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if len(submission.question) > 500:
        raise HTTPException(status_code=400, detail="Question too long (max 500 characters).")

    # Import here to avoid circular imports
    from backend.main import question_manager, filter_and_queue_question

    question = question_manager.submit_question(
        question=submission.question.strip(),
        name=submission.name.strip() if submission.name else None,
    )

    # Trigger async filtering
    import asyncio
    asyncio.create_task(filter_and_queue_question(question.id))

    return JSONResponse(
        status_code=201,
        content={
            "status": "submitted",
            "message": "Your question has been submitted! We'll get to it during Q&A.",
            "question_id": question.id,
        },
    )


@router.get("/list")
async def list_questions():
    """List all submitted questions (for moderator view)."""
    from backend.main import question_manager

    return {
        "total": question_manager.total_questions,
        "pending": question_manager.pending_count,
        "approved": question_manager.approved_count,
        "questions": question_manager.get_all_questions(),
    }


@router.get("/pending")
async def get_pending_questions():
    """Get pending questions awaiting review."""
    from backend.main import question_manager

    pending = question_manager.get_pending_questions()
    return {
        "count": len(pending),
        "questions": [
            {"id": q.id, "name": q.name or "Anonymous", "question": q.question}
            for q in pending
        ],
    }
