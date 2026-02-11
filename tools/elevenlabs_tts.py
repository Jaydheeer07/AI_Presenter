"""ElevenLabs TTS wrapper tool.

Standalone script for generating audio via ElevenLabs API.
Used for testing and one-off generation outside the main application.

Usage:
    python tools/elevenlabs_tts.py --text "Hello world" --output test.mp3
    python tools/elevenlabs_tts.py --credits  # Check remaining credits
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Add project root to path for imports
sys.path.insert(0, str(project_root))


async def generate(text: str, output_path: str):
    """Generate audio from text and save to file."""
    from backend.services.tts_service import synthesize_speech

    print(f"Generating audio for: {text[:80]}...")
    audio_bytes = await synthesize_speech(text, output_path)
    print(f"Saved to: {output_path} ({len(audio_bytes)} bytes)")


async def check_credits():
    """Check remaining ElevenLabs credits."""
    from backend.services.tts_service import get_remaining_credits

    credits = await get_remaining_credits()
    if credits is not None:
        print(f"Remaining ElevenLabs credits: {credits:,}")
    else:
        print("Failed to check credits. Is your API key configured?")


def main():
    parser = argparse.ArgumentParser(description="ElevenLabs TTS tool")
    parser.add_argument("--text", help="Text to synthesize")
    parser.add_argument("--output", default="output.mp3", help="Output file path")
    parser.add_argument("--credits", action="store_true", help="Check remaining credits")
    args = parser.parse_args()

    if args.credits:
        asyncio.run(check_credits())
    elif args.text:
        asyncio.run(generate(args.text, args.output))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
