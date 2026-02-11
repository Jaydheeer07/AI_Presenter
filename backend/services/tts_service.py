"""TTS service for live speech synthesis using ElevenLabs API.

Used during the presentation for real-time responses (audience interaction, Q&A).
Pre-generated audio is handled by the Kokoro batch tool, not this service.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


def _get_headers() -> dict:
    """Get ElevenLabs API headers."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    return {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }


def _get_voice_id() -> str:
    """Get the configured ElevenLabs voice ID."""
    return os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default: Rachel


async def synthesize_speech(text: str, output_path: Optional[str] = None) -> bytes:
    """Synthesize speech from text using ElevenLabs API.

    Args:
        text: The text to convert to speech.
        output_path: Optional file path to save the audio. If None, returns bytes only.

    Returns:
        Audio bytes (MP3 format).

    Raises:
        httpx.HTTPStatusError: If the API request fails.
    """
    voice_id = _get_voice_id()
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, headers=_get_headers())
            response.raise_for_status()
            audio_bytes = response.content

            if output_path:
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
                logger.info(f"Audio saved to {output_path}")

            return audio_bytes

        except httpx.HTTPStatusError as e:
            logger.error(f"ElevenLabs API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}")
            raise


async def stream_speech(text: str):
    """Stream speech synthesis from ElevenLabs API.

    Yields audio chunks as they arrive for lower-latency playback.

    Args:
        text: The text to convert to speech.

    Yields:
        Audio bytes chunks.
    """
    voice_id = _get_voice_id()
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}/stream"

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream("POST", url, json=payload, headers=_get_headers()) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=1024):
                    yield chunk
        except httpx.HTTPStatusError as e:
            logger.error(f"ElevenLabs stream error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"ElevenLabs stream error: {e}")
            raise


async def get_remaining_credits() -> Optional[int]:
    """Check remaining ElevenLabs API credits.

    Returns:
        Remaining character credits, or None if check fails.
    """
    url = f"{ELEVENLABS_BASE_URL}/user/subscription"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=_get_headers())
            response.raise_for_status()
            data = response.json()
            remaining = data.get("character_limit", 0) - data.get("character_count", 0)
            logger.info(f"ElevenLabs credits remaining: {remaining}")
            return remaining
        except Exception as e:
            logger.error(f"Failed to check ElevenLabs credits: {e}")
            return None
