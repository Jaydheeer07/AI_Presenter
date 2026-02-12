"""Quick test script to verify Kokoro and ElevenLabs TTS connectivity."""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")
sys.path.insert(0, str(project_root))


async def test_elevenlabs():
    """Test ElevenLabs TTS."""
    from backend.services.tts_service import (
        get_remaining_credits,
        is_configured,
        list_voices,
        synthesize_speech,
    )

    print("=" * 50)
    print("  ELEVENLABS TTS TEST")
    print("=" * 50)

    configured = is_configured()
    print(f"  Configured: {configured}")
    print(f"  API Key:    {'set' if os.getenv('ELEVENLABS_API_KEY') else 'MISSING'}")
    print(f"  Voice ID:   {os.getenv('ELEVENLABS_VOICE_ID', 'MISSING')}")

    if not configured:
        print("\n  [SKIP] ElevenLabs not configured.")
        return False

    # Check credits
    credits = await get_remaining_credits()
    print(f"  Credits:    {credits:,}" if credits else "  Credits:    FAILED")

    # List voices
    voices = await list_voices()
    if voices:
        print(f"  Voices:     {len(voices)} available")
        for v in voices[:5]:
            print(f"    - {v['name']} ({v['voice_id'][:12]}...)")
        if len(voices) > 5:
            print(f"    ... and {len(voices) - 5} more")
    else:
        print("  Voices:     FAILED to list")

    # Generate test audio
    print("\n  Generating test audio...")
    try:
        output_path = str(project_root / ".tmp" / "elevenlabs_test.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        audio = await synthesize_speech(
            "Hello! I am DexIQ, your AI presenter.",
            output_path=output_path,
        )
        print(f"  [OK] Generated {len(audio):,} bytes -> {output_path}")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_kokoro():
    """Test Kokoro TTS via OpenAI-compatible REST API."""
    import httpx

    print("\n" + "=" * 50)
    print("  KOKORO TTS TEST")
    print("=" * 50)

    kokoro_url = os.getenv("KOKORO_API_URL", "http://localhost:8880")
    voice = os.getenv("KOKORO_VOICE", "af_heart")
    base = kokoro_url.rstrip("/")
    print(f"  URL:   {base}")
    print(f"  Voice: {voice}")

    # Test health
    print("\n  Checking Kokoro health...")
    try:
        resp = httpx.get(f"{base}/health", timeout=5.0)
        print(f"  [OK] Health: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"  [FAIL] Cannot reach Kokoro at {base}: {e}")
        return False

    # List voices
    try:
        resp = httpx.get(f"{base}/v1/audio/voices", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            voices = data if isinstance(data, list) else data.get("voices", [])
            print(f"  Voices: {len(voices)} available")
    except Exception:
        pass

    # Generate test audio
    print("  Generating test audio...")
    try:
        output_path = str(project_root / ".tmp" / "kokoro_test.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        resp = httpx.post(
            f"{base}/v1/audio/speech",
            json={
                "input": "Hello! I am DexIQ, your AI presenter.",
                "voice": voice,
                "response_format": "mp3",
                "speed": 1.0,
                "stream": False,
            },
            timeout=60.0,
        )
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(resp.content)

        size_kb = len(resp.content) / 1024
        print(f"  [OK] Generated {size_kb:.1f} KB -> {output_path}")
        return True
    except httpx.HTTPStatusError as e:
        print(f"  [FAIL] API error {e.response.status_code}: {e.response.text[:200]}")
        return False
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def main():
    print("\nDexIQ TTS Connection Tests\n")

    kokoro_ok = test_kokoro()
    elevenlabs_ok = asyncio.run(test_elevenlabs())

    print("\n" + "=" * 50)
    print("  RESULTS")
    print("=" * 50)
    print(f"  Kokoro:     {'PASS' if kokoro_ok else 'FAIL'}")
    print(f"  ElevenLabs: {'PASS' if elevenlabs_ok else 'FAIL'}")
    print()


if __name__ == "__main__":
    main()
