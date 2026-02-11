"""Kokoro TTS batch generation tool.

Reads narration scripts from config/presentation.yaml and generates
MP3 audio files for each slide using Kokoro TTS (local).

Usage:
    python tools/kokoro_batch_generate.py --config config/presentation.yaml --output frontend/audio/
"""

import argparse
import os
import sys
from pathlib import Path

import yaml


def load_presentation_config(config_path: str) -> dict:
    """Load presentation configuration from YAML."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_audio(text: str, output_path: str, voice: str = "af_heart") -> bool:
    """Generate audio from text using Kokoro TTS.

    Args:
        text: The narration text to synthesize.
        output_path: Path to save the output MP3 file.
        voice: Kokoro voice ID to use.

    Returns:
        True if generation succeeded, False otherwise.
    """
    try:
        from kokoro import KPipeline

        pipeline = KPipeline(lang_code="a")
        generator = pipeline(text, voice=voice)

        # Kokoro yields (graphemes, phonemes, audio) tuples
        audio_segments = []
        for _, _, audio in generator:
            audio_segments.append(audio)

        if not audio_segments:
            print(f"  [WARN] No audio generated for: {output_path}")
            return False

        # Concatenate and save
        import numpy as np
        import soundfile as sf

        full_audio = np.concatenate(audio_segments)

        # Save as WAV first, then convert to MP3
        wav_path = output_path.replace(".mp3", ".wav")
        sf.write(wav_path, full_audio, 24000)

        # Convert to MP3 using pydub
        from pydub import AudioSegment

        audio_seg = AudioSegment.from_wav(wav_path)
        audio_seg.export(output_path, format="mp3", bitrate="192k")

        # Clean up WAV
        os.remove(wav_path)

        print(f"  [OK] Generated: {output_path}")
        return True

    except ImportError as e:
        print(f"  [ERROR] Missing dependency: {e}")
        print("  Install with: pip install kokoro soundfile numpy pydub")
        return False
    except Exception as e:
        print(f"  [ERROR] Failed to generate {output_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Batch generate narration audio with Kokoro TTS")
    parser.add_argument("--config", default="config/presentation.yaml", help="Presentation config YAML")
    parser.add_argument("--output", default="frontend/audio/", help="Output directory for audio files")
    parser.add_argument("--voice", default="af_heart", help="Kokoro voice ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated without generating")
    args = parser.parse_args()

    # Resolve paths relative to project root
    project_root = Path(__file__).parent.parent
    config_path = project_root / args.config
    output_dir = project_root / args.output

    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_presentation_config(str(config_path))
    slides = config.get("slides", [])

    print(f"Loaded {len(slides)} slides from {config_path}")
    print(f"Output directory: {output_dir}")
    print(f"Voice: {args.voice}")
    print()

    generated = 0
    skipped = 0
    failed = 0

    for slide in slides:
        slide_id = slide.get("id", "?")
        title = slide.get("title", "Untitled")
        narration = slide.get("narration")
        audio_file = slide.get("audio_file")

        if not narration or not audio_file:
            print(f"Slide {slide_id} ({title}): No narration — skipping")
            skipped += 1
            continue

        output_path = str(output_dir / Path(audio_file).name)

        print(f"Slide {slide_id} ({title}):")
        print(f"  Text: {narration[:80]}...")

        if args.dry_run:
            print(f"  [DRY RUN] Would generate: {output_path}")
            generated += 1
            continue

        if generate_audio(narration.strip(), output_path, args.voice):
            generated += 1
        else:
            failed += 1

        # Also generate interaction question audio if present
        interaction = slide.get("interaction")
        if interaction:
            q_audio = interaction.get("question_audio")
            q_text = interaction.get("question")
            if q_audio and q_text:
                q_output = str(output_dir / Path(q_audio).name)
                print(f"  Interaction question: {q_text[:60]}...")
                if args.dry_run:
                    print(f"  [DRY RUN] Would generate: {q_output}")
                elif generate_audio(q_text.strip(), q_output, args.voice):
                    generated += 1
                else:
                    failed += 1

    print()
    print(f"Done! Generated: {generated}, Skipped: {skipped}, Failed: {failed}")


if __name__ == "__main__":
    main()
