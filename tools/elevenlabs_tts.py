"""ElevenLabs TTS wrapper tool.

Standalone script for generating audio via ElevenLabs API.
Used for testing and one-off generation outside the main application.

Usage:
    python tools/elevenlabs_tts.py --text "Hello world" --output test.mp3
    python tools/elevenlabs_tts.py --text "Hello" --model eleven_turbo_v2_5
    python tools/elevenlabs_tts.py --credits
    python tools/elevenlabs_tts.py --voices
    python tools/elevenlabs_tts.py --status
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Add project root to path for imports
sys.path.insert(0, str(project_root))


async def generate(text: str, output_path: str, model: str | None = None):
    """Generate audio from text and save to file."""
    from backend.services.tts_service import synthesize_speech

    print(f"Text: {text[:100]}{'...' if len(text) > 100 else ''}")
    print(f"Model: {model or 'default'}")
    print(f"Output: {output_path}")
    print()

    start = time.monotonic()
    audio_bytes = await synthesize_speech(text, output_path, model=model)
    elapsed = time.monotonic() - start

    size_kb = len(audio_bytes) / 1024
    print(f"Generated: {size_kb:.1f} KB in {elapsed:.2f}s")
    print(f"Saved to: {output_path}")


async def stream_test(text: str, output_path: str, model: str | None = None):
    """Test streaming TTS and save the assembled output."""
    from backend.services.tts_service import stream_speech

    print(f"Streaming TTS for: {text[:100]}{'...' if len(text) > 100 else ''}")
    print(f"Model: {model or 'default'}")
    print()

    start = time.monotonic()
    chunks = []
    chunk_count = 0

    async for chunk in stream_speech(text, model=model):
        chunks.append(chunk)
        chunk_count += 1
        if chunk_count == 1:
            ttfb = time.monotonic() - start
            print(f"First chunk received in {ttfb:.2f}s")

    elapsed = time.monotonic() - start
    total_bytes = sum(len(c) for c in chunks)

    # Save assembled audio
    with open(output_path, "wb") as f:
        for chunk in chunks:
            f.write(chunk)

    print(f"Stream complete: {chunk_count} chunks, {total_bytes / 1024:.1f} KB in {elapsed:.2f}s")
    print(f"Saved to: {output_path}")


async def check_credits():
    """Check remaining ElevenLabs credits."""
    from backend.services.tts_service import get_remaining_credits

    credits = await get_remaining_credits()
    if credits is not None:
        print(f"Remaining ElevenLabs credits: {credits:,}")
    else:
        print("Failed to check credits. Is your API key configured?")


async def list_voices():
    """List available ElevenLabs voices."""
    from backend.services.tts_service import list_voices

    voices = await list_voices()
    if voices is None:
        print("Failed to list voices. Is your API key configured?")
        return

    print(f"Available voices ({len(voices)}):")
    print(f"{'Name':<30s} {'Voice ID':<30s} {'Category':<15s}")
    print("-" * 75)
    for v in voices:
        print(f"{v['name']:<30s} {v['voice_id']:<30s} {v.get('category', ''):<15s}")


async def check_status():
    """Check overall ElevenLabs configuration and status."""
    from backend.services.tts_service import is_configured, get_remaining_credits

    configured = is_configured()
    print(f"API Key set:   {'Yes' if os.getenv('ELEVENLABS_API_KEY') else 'No'}")
    print(f"Voice ID set:  {'Yes' if os.getenv('ELEVENLABS_VOICE_ID') else 'No'}")
    print(f"Voice ID:      {os.getenv('ELEVENLABS_VOICE_ID', 'not set')}")
    print(f"Model:         {os.getenv('ELEVENLABS_MODEL', 'eleven_multilingual_v2 (default)')}")
    print(f"Output format: {os.getenv('ELEVENLABS_OUTPUT_FORMAT', 'mp3_44100_128 (default)')}")
    print(f"Configured:    {'Yes' if configured else 'No'}")

    if configured:
        credits = await get_remaining_credits()
        if credits is not None:
            print(f"Credits:       {credits:,}")
        else:
            print("Credits:       Failed to check")


def main():
    parser = argparse.ArgumentParser(
        description="ElevenLabs TTS tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/elevenlabs_tts.py --status
  python tools/elevenlabs_tts.py --text "Hello, I'm DexIQ" --output test.mp3
  python tools/elevenlabs_tts.py --text "Hello" --stream --output test_stream.mp3
  python tools/elevenlabs_tts.py --text "Fast test" --model eleven_turbo_v2_5
  python tools/elevenlabs_tts.py --credits
  python tools/elevenlabs_tts.py --voices
""",
    )
    parser.add_argument("--text", help="Text to synthesize")
    parser.add_argument("--output", default=".tmp/tts_test.mp3", help="Output file path")
    parser.add_argument("--model", help="Override TTS model (e.g., eleven_turbo_v2_5)")
    parser.add_argument("--stream", action="store_true", help="Use streaming mode")
    parser.add_argument("--credits", action="store_true", help="Check remaining credits")
    parser.add_argument("--voices", action="store_true", help="List available voices")
    parser.add_argument("--status", action="store_true", help="Check configuration status")
    args = parser.parse_args()

    # Ensure output directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    if args.status:
        asyncio.run(check_status())
    elif args.credits:
        asyncio.run(check_credits())
    elif args.voices:
        asyncio.run(list_voices())
    elif args.text:
        if args.stream:
            asyncio.run(stream_test(args.text, args.output, args.model))
        else:
            asyncio.run(generate(args.text, args.output, args.model))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
