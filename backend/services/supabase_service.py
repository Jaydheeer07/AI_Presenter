"""Supabase persistence layer for audience Q&A questions.

Provides lazy-initialised Supabase client and helper functions for
persisting, updating, and retrieving questions from the cloud database.

Environment variables required:
    SUPABASE_URL      — your Supabase project URL
    SUPABASE_ANON_KEY — your Supabase anon/public key
    QA_SESSION_ID     — unique identifier for this presentation session
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Lazily initialise and return the Supabase client."""
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        logger.warning("SUPABASE_URL or SUPABASE_ANON_KEY not set — Supabase persistence disabled.")
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase client initialised.")
    except Exception as e:
        logger.error(f"Failed to initialise Supabase client: {e}")
        return None

    return _client


def persist_question(question_id: int, name: Optional[str], question: str) -> bool:
    """Insert a new audience question into Supabase.

    Args:
        question_id: Local in-memory question ID (used as reference only).
        name: Submitter's name, or None for anonymous.
        question: The question text.

    Returns:
        True if persisted successfully, False otherwise.
    """
    client = _get_client()
    if not client:
        return False

    session_id = os.getenv("QA_SESSION_ID", "default")

    try:
        client.table("questions").insert({
            "session_id": session_id,
            "local_id": question_id,
            "name": name or "Anonymous",
            "question": question,
            "status": "pending",
        }).execute()
        logger.info(f"Question #{question_id} persisted to Supabase.")
        return True
    except Exception as e:
        logger.error(f"Failed to persist question #{question_id} to Supabase: {e}")
        return False


def update_question_status(question_id: int, status: str, answer: Optional[str] = None) -> bool:
    """Update the status (and optionally answer) of a question in Supabase.

    Args:
        question_id: Local in-memory question ID.
        status: New status string (e.g. 'answered', 'flagged').
        answer: The generated answer text, if applicable.

    Returns:
        True if updated successfully, False otherwise.
    """
    client = _get_client()
    if not client:
        return False

    session_id = os.getenv("QA_SESSION_ID", "default")

    try:
        payload: dict = {"status": status}
        if answer is not None:
            payload["answer"] = answer

        client.table("questions").update(payload).eq("session_id", session_id).eq("local_id", question_id).execute()
        logger.info(f"Question #{question_id} status updated to '{status}' in Supabase.")
        return True
    except Exception as e:
        logger.error(f"Failed to update question #{question_id} in Supabase: {e}")
        return False


def get_session_questions(session_id: Optional[str] = None) -> list[dict]:
    """Retrieve all questions for a session from Supabase.

    Args:
        session_id: Session ID to query. Defaults to QA_SESSION_ID env var.

    Returns:
        List of question dicts, or empty list on failure.
    """
    client = _get_client()
    if not client:
        return []

    sid = session_id or os.getenv("QA_SESSION_ID", "default")

    try:
        response = client.table("questions").select("*").eq("session_id", sid).order("created_at").execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to fetch questions from Supabase: {e}")
        return []
