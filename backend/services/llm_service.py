"""LLM service for generating live responses using OpenAI GPT-4o.

Handles audience interaction responses and Q&A answers.
"""

import logging
import os
from typing import Optional

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# Load prompts from config
_prompts_cache: Optional[dict] = None


def _load_prompts() -> dict:
    """Load system prompts from config/prompts.yaml."""
    global _prompts_cache
    if _prompts_cache is not None:
        return _prompts_cache

    prompts_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "prompts.yaml"
    )
    try:
        with open(prompts_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            _prompts_cache = data.get("system_prompts", {})
    except FileNotFoundError:
        logger.warning(f"Prompts file not found at {prompts_path}, using defaults.")
        _prompts_cache = {}

    return _prompts_cache


def _get_llm() -> ChatOpenAI:
    """Create an OpenAI LLM instance."""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.7,
        max_completion_tokens=4096,
    )


async def generate_audience_response(
    target_name: str,
    target_role: str,
    question: str,
    answer_summary: str,
) -> str:
    """Generate a personalized response to an audience member's answer.

    Args:
        target_name: Name of the audience member.
        target_role: Their role/title.
        question: The question that was asked.
        answer_summary: The puppeteer's summary of their answer.

    Returns:
        Generated response text (2-3 sentences).
    """
    prompts = _load_prompts()
    system_template = prompts.get("audience_response", "")

    system_prompt = system_template.format(
        target_name=target_name,
        target_role=target_role,
        question=question,
        answer_summary=answer_summary,
    )

    llm = _get_llm()
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{target_name} said: {answer_summary}"),
        ])
        text = (response.content or "").strip()
        if not text:
            logger.warning(
                f"LLM returned empty content for audience response. "
                f"finish_reason={response.response_metadata.get('finish_reason')}, "
                f"usage={response.response_metadata.get('token_usage')}"
            )
            text = f"Thank you for sharing that, {target_name}. That's a great perspective."
        return text
    except Exception as e:
        logger.error(f"LLM error generating audience response: {e}")
        return f"Thank you for sharing that, {target_name}. That's a great perspective."


async def generate_qa_answer(question: str) -> str:
    """Generate an answer to an audience Q&A question.

    Args:
        question: The audience member's question.

    Returns:
        Generated answer text (3-5 sentences).
    """
    prompts = _load_prompts()
    system_template = prompts.get("qa_answer", "")

    system_prompt = system_template.format(question=question)

    llm = _get_llm()
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ])
        text = (response.content or "").strip()
        if not text:
            logger.warning(
                f"LLM returned empty content for Q&A answer. "
                f"finish_reason={response.response_metadata.get('finish_reason')}, "
                f"usage={response.response_metadata.get('token_usage')}"
            )
            text = "That's a great question. I'd recommend exploring the tools we discussed today to find the best fit for your needs."
        return text
    except Exception as e:
        logger.error(f"LLM error generating Q&A answer: {e}")
        return "That's a great question. I'd recommend exploring the tools we discussed today to find the best fit for your needs."


async def filter_question(question: str) -> dict:
    """Score and filter an audience question for relevance.

    Args:
        question: The submitted question text.

    Returns:
        Dict with keys: score (int), flag (str|None), reason (str).
    """
    prompts = _load_prompts()
    system_template = prompts.get("question_filter", "")

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.0,
        max_completion_tokens=512,
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_template),
            HumanMessage(content=question),
        ])
        import json
        result = json.loads(response.content.strip())
        return {
            "score": result.get("score", 5),
            "flag": result.get("flag"),
            "reason": result.get("reason", ""),
        }
    except Exception as e:
        logger.error(f"LLM error filtering question: {e}")
        return {"score": 5, "flag": None, "reason": "Filter unavailable, defaulting to neutral score."}
