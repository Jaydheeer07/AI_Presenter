"""Audio utility functions.

Format conversion, normalization, and validation for audio files.

Usage:
    python tools/audio_utils.py --normalize frontend/audio/
    python tools/audio_utils.py --check frontend/audio/
"""

import argparse
import os
import sys
from pathlib import Path


def normalize_audio(input_path: str, target_db: float = -20.0) -> bool:
    """Normalize audio file to a target dB level.

    Args:
        input_path: Path to the audio file.
        target_db: Target loudness in dB (default -20.0).

    Returns:
        True if normalization succeeded.
    """
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(input_path)
        change_in_db = target_db - audio.dBFS
        normalized = audio.apply_gain(change_in_db)
        normalized.export(input_path, format=Path(input_path).suffix.lstrip("."))
        print(f"  [OK] Normalized: {input_path} (adjusted {change_in_db:+.1f} dB)")
        return True
    except Exception as e:
        print(f"  [ERROR] {input_path}: {e}")
        return False


def check_audio_files(audio_dir: str) -> dict:
    """Check all audio files in a directory for validity.

    Args:
        audio_dir: Path to the audio directory.

    Returns:
        Dict with counts of valid, invalid, and missing files.
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        print("Error: pydub not installed. Run: pip install pydub")
        sys.exit(1)

    results = {"valid": 0, "invalid": 0, "files": []}

    audio_path = Path(audio_dir)
    if not audio_path.exists():
        print(f"Directory not found: {audio_dir}")
        return results

    for f in sorted(audio_path.glob("*.mp3")):
        try:
            audio = AudioSegment.from_mp3(str(f))
            duration = len(audio) / 1000.0
            db = audio.dBFS
            results["valid"] += 1
            results["files"].append({
                "name": f.name,
                "duration": f"{duration:.1f}s",
                "loudness": f"{db:.1f} dB",
                "status": "OK",
            })
            print(f"  [OK] {f.name}: {duration:.1f}s, {db:.1f} dB")
        except Exception as e:
            results["invalid"] += 1
            results["files"].append({
                "name": f.name,
                "status": f"ERROR: {e}",
            })
            print(f"  [ERROR] {f.name}: {e}")

    return results


def convert_wav_to_mp3(input_path: str, output_path: str = None, bitrate: str = "192k") -> bool:
    """Convert a WAV file to MP3.

    Args:
        input_path: Path to the WAV file.
        output_path: Path for the output MP3 (default: same name with .mp3).
        bitrate: MP3 bitrate (default 192k).

    Returns:
        True if conversion succeeded.
    """
    if output_path is None:
        output_path = str(Path(input_path).with_suffix(".mp3"))

    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_wav(input_path)
        audio.export(output_path, format="mp3", bitrate=bitrate)
        print(f"  [OK] Converted: {input_path} → {output_path}")
        return True
    except Exception as e:
        print(f"  [ERROR] Conversion failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Audio utility tools")
    parser.add_argument("--normalize", metavar="DIR", help="Normalize all MP3s in directory")
    parser.add_argument("--check", metavar="DIR", help="Check all audio files in directory")
    parser.add_argument("--convert", metavar="FILE", help="Convert WAV to MP3")
    parser.add_argument("--target-db", type=float, default=-20.0, help="Target dB for normalization")
    args = parser.parse_args()

    if args.check:
        print(f"Checking audio files in: {args.check}")
        results = check_audio_files(args.check)
        print(f"\nValid: {results['valid']}, Invalid: {results['invalid']}")

    elif args.normalize:
        print(f"Normalizing audio files in: {args.normalize} (target: {args.target_db} dB)")
        audio_dir = Path(args.normalize)
        for f in sorted(audio_dir.glob("*.mp3")):
            normalize_audio(str(f), args.target_db)

    elif args.convert:
        convert_wav_to_mp3(args.convert)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
