"""TTS service for live speech synthesis using ElevenLabs API.

Used during the presentation for real-time responses (audience interaction, Q&A).
Pre-generated audio is handled by the Kokoro batch tool, not this service.

Supports two modes:
  1. Full synthesis  — synthesize_speech() returns complete audio bytes
  2. Streaming       — stream_speech() yields audio chunks for low-latency playback
"""

import asyncio
import base64
import json
import logging
import os
import time
from typing import AsyncGenerator, Optional

import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# Default voice settings — configurable via .env
# Values match ElevenLabs UI percentages: 50% = 0.5, 75% = 0.75, etc.
DEFAULT_VOICE_SETTINGS = {
    "stability": float(os.getenv("ELEVENLABS_STABILITY", "0.5")),
    "similarity_boost": float(os.getenv("ELEVENLABS_SIMILARITY_BOOST", "0.75")),
    "style": float(os.getenv("ELEVENLABS_STYLE", "0.0")),
    "use_speaker_boost": os.getenv("ELEVENLABS_SPEAKER_BOOST", "false").lower() == "true",
}

# Model selection
DEFAULT_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")

# Output format: mp3_44100_128 is a good balance of quality and size
DEFAULT_OUTPUT_FORMAT = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")


def _get_api_key() -> str:
    """Get ElevenLabs API key."""
    key = os.getenv("ELEVENLABS_API_KEY", "")
    if not key:
        logger.warning("ELEVENLABS_API_KEY not set. Live TTS will fail.")
    return key


def _get_headers() -> dict:
    """Get ElevenLabs API headers."""
    return {
        "xi-api-key": _get_api_key(),
        "Content-Type": "application/json",
    }


def _get_voice_id() -> str:
    """Get the configured ElevenLabs voice ID."""
    return os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default: Rachel


def _build_payload(text: str, model: str | None = None) -> dict:
    """Build the TTS request payload."""
    return {
        "text": text,
        "model_id": model or DEFAULT_MODEL,
        "voice_settings": DEFAULT_VOICE_SETTINGS,
    }


async def synthesize_speech(
    text: str,
    output_path: Optional[str] = None,
    model: Optional[str] = None,
    max_retries: int = 2,
) -> bytes:
    """Synthesize speech from text using ElevenLabs API.

    Args:
        text: The text to convert to speech.
        output_path: Optional file path to save the audio. If None, returns bytes only.
        model: Override the default model (e.g., "eleven_turbo_v2_5" for speed).
        max_retries: Number of retries on transient failures.

    Returns:
        Audio bytes (MP3 format).

    Raises:
        httpx.HTTPStatusError: If the API request fails after retries.
    """
    voice_id = _get_voice_id()
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"
    params = {"output_format": DEFAULT_OUTPUT_FORMAT}
    payload = _build_payload(text, model)

    start_time = time.monotonic()

    for attempt in range(max_retries + 1):
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url, json=payload, headers=_get_headers(), params=params
                )
                response.raise_for_status()
                audio_bytes = response.content

                elapsed = time.monotonic() - start_time
                logger.info(
                    f"TTS synthesized {len(text)} chars -> {len(audio_bytes)} bytes "
                    f"in {elapsed:.2f}s (model: {payload['model_id']})"
                )

                if output_path:
                    with open(output_path, "wb") as f:
                        f.write(audio_bytes)
                    logger.info(f"Audio saved to {output_path}")

                return audio_bytes

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429 and attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited (429). Retrying in {wait}s... (attempt {attempt + 1})")
                    await asyncio.sleep(wait)
                    continue
                logger.error(f"ElevenLabs API error: {status} - {e.response.text}")
                raise
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning(f"Connection error: {e}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                logger.error(f"ElevenLabs TTS connection failed after {max_retries + 1} attempts: {e}")
                raise
            except Exception as e:
                logger.error(f"ElevenLabs TTS error: {e}")
                raise

    # Should not reach here, but just in case
    raise RuntimeError("TTS synthesis failed after all retries")


async def stream_speech(
    text: str,
    model: Optional[str] = None,
    chunk_size: int = 1024,
) -> AsyncGenerator[bytes, None]:
    """Stream speech synthesis from ElevenLabs HTTP streaming API.

    Yields audio chunks as they arrive for lower-latency playback.
    The frontend can start playing audio before the full response is ready.

    Args:
        text: The text to convert to speech.
        model: Override the default model. Use "eleven_turbo_v2_5" for lowest latency.
        chunk_size: Size of audio chunks to yield (bytes).

    Yields:
        Audio bytes chunks (MP3 format).
    """
    voice_id = _get_voice_id()
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}/stream"
    params = {"output_format": DEFAULT_OUTPUT_FORMAT}
    payload = _build_payload(text, model)

    start_time = time.monotonic()
    total_bytes = 0
    chunk_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream(
                "POST", url, json=payload, headers=_get_headers(), params=params
            ) as response:
                response.raise_for_status()

                first_chunk = True
                async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                    if first_chunk:
                        ttfb = time.monotonic() - start_time
                        logger.info(f"TTS stream first chunk in {ttfb:.2f}s")
                        first_chunk = False

                    total_bytes += len(chunk)
                    chunk_count += 1
                    yield chunk

            elapsed = time.monotonic() - start_time
            logger.info(
                f"TTS stream complete: {chunk_count} chunks, "
                f"{total_bytes} bytes in {elapsed:.2f}s"
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"ElevenLabs stream error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"ElevenLabs stream error: {e}")
            raise


async def stream_speech_as_base64(
    text: str,
    model: Optional[str] = None,
    chunk_size: int = 4096,
) -> AsyncGenerator[dict, None]:
    """Stream speech and yield base64-encoded chunks ready for WebSocket transport.

    Each yielded dict has the format:
        {"type": "audio_chunk", "data": {"chunk": <base64>, "index": N, "final": bool}}

    This is designed to be sent directly over the presenter WebSocket.

    Args:
        text: The text to convert to speech.
        model: Override the default model.
        chunk_size: Size of raw audio chunks before base64 encoding.

    Yields:
        Dicts with base64-encoded audio chunks.
    """
    index = 0
    async for chunk in stream_speech(text, model=model, chunk_size=chunk_size):
        b64_chunk = base64.b64encode(chunk).decode("utf-8")
        yield {
            "type": "audio_chunk",
            "data": {
                "chunk": b64_chunk,
                "index": index,
                "final": False,
            },
        }
        index += 1

    # Send final marker
    yield {
        "type": "audio_chunk",
        "data": {
            "chunk": "",
            "index": index,
            "final": True,
        },
    }


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
            logger.info(f"ElevenLabs credits remaining: {remaining:,}")
            return remaining
        except Exception as e:
            logger.error(f"Failed to check ElevenLabs credits: {e}")
            return None


async def list_voices() -> list[dict] | None:
    """List available ElevenLabs voices.

    Returns:
        List of voice dicts with voice_id and name, or None on failure.
    """
    url = f"{ELEVENLABS_BASE_URL}/voices"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=_get_headers())
            response.raise_for_status()
            data = response.json()
            voices = [
                {"voice_id": v["voice_id"], "name": v["name"], "category": v.get("category", "")}
                for v in data.get("voices", [])
            ]
            return voices
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            return None


def is_configured() -> bool:
    """Check if ElevenLabs API is configured (API key and voice ID set)."""
    return bool(os.getenv("ELEVENLABS_API_KEY")) and bool(os.getenv("ELEVENLABS_VOICE_ID"))
