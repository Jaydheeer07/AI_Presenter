"""REST endpoints for testing and managing the ElevenLabs TTS service.

Provides endpoints to test live TTS, check credits, and list voices
without needing to run the full presentation flow.
"""

import base64
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from backend.services.tts_service import (
    get_remaining_credits,
    is_configured,
    list_voices,
    stream_speech_as_base64,
    synthesize_speech,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])


class TTSTestRequest(BaseModel):
    """Request body for TTS test endpoint."""
    text: str = "Hello! I'm DexIQ, your AI presenter. This is a test of the live speech system."
    model: str | None = None


@router.get("/status")
async def tts_status():
    """Check if ElevenLabs TTS is configured and ready."""
    configured = is_configured()
    credits = None
    if configured:
        credits = await get_remaining_credits()

    return {
        "configured": configured,
        "credits_remaining": credits,
        "status": "ready" if configured else "not_configured",
        "message": "ElevenLabs TTS is ready." if configured
                   else "Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env",
    }


@router.post("/test")
async def test_tts(request: TTSTestRequest):
    """Test TTS synthesis — returns audio as base64 and metadata.

    Use this to verify your ElevenLabs setup before the presentation.
    """
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail="ElevenLabs not configured. Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env",
        )

    try:
        audio_bytes = await synthesize_speech(request.text, model=request.model)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return {
            "status": "ok",
            "text": request.text,
            "audio_base64": audio_b64,
            "audio_size_bytes": len(audio_bytes),
            "text_chars": len(request.text),
        }
    except Exception as e:
        logger.error(f"TTS test failed: {e}")
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {e}")


@router.post("/test/audio")
async def test_tts_audio(request: TTSTestRequest):
    """Test TTS synthesis — returns raw MP3 audio for direct playback.

    Useful for testing in a browser: fetch this endpoint and play the response.
    """
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail="ElevenLabs not configured.",
        )

    try:
        audio_bytes = await synthesize_speech(request.text, model=request.model)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=tts_test.mp3"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {e}")


@router.get("/credits")
async def check_credits():
    """Check remaining ElevenLabs API credits."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="ElevenLabs not configured.")

    credits = await get_remaining_credits()
    if credits is None:
        raise HTTPException(status_code=500, detail="Failed to check credits.")

    return {"credits_remaining": credits}


@router.get("/voices")
async def get_voices():
    """List available ElevenLabs voices."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="ElevenLabs not configured.")

    voices = await list_voices()
    if voices is None:
        raise HTTPException(status_code=500, detail="Failed to list voices.")

    return {"voices": voices, "count": len(voices)}
