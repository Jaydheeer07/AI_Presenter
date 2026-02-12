"""Audio manifest manager.

Scans frontend/audio/ and config/presentation.yaml to build a manifest
tracking which audio files exist, their source, duration, and status.

Usage:
    python tools/audio_manifest.py                  # Scan and update manifest
    python tools/audio_manifest.py --report         # Print a summary report
    python tools/audio_manifest.py --missing-only   # Show only missing files
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml


def load_presentation_config(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_expected_files(config: dict) -> list[dict]:
    """Get all expected audio files from the presentation config."""
    expected = []
    for slide in config.get("slides", []):
        slide_id = slide.get("id", -1)
        title = slide.get("title", "Untitled")
        audio_file = slide.get("audio_file")
        narration = slide.get("narration")

        if audio_file:
            expected.append({
                "filename": Path(audio_file).name,
                "slide_id": slide_id,
                "title": title,
                "type": "narration",
                "text_chars": len(narration.strip()) if narration else 0,
            })

        interaction = slide.get("interaction")
        if interaction:
            q_audio = interaction.get("question_audio")
            q_text = interaction.get("question", "")
            if q_audio:
                expected.append({
                    "filename": Path(q_audio).name,
                    "slide_id": slide_id,
                    "title": f"{title} — Interaction Q",
                    "type": "interaction",
                    "text_chars": len(q_text.strip()) if q_text else 0,
                })

    return expected


def get_audio_file_info(file_path: Path) -> dict | None:
    """Get metadata for an audio file (duration, size)."""
    if not file_path.exists():
        return None

    info = {
        "size_bytes": file_path.stat().st_size,
        "size_kb": round(file_path.stat().st_size / 1024, 1),
        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
    }

    # Try to get duration via pydub
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(str(file_path))
        info["duration_seconds"] = round(len(audio) / 1000.0, 1)
        info["loudness_db"] = round(audio.dBFS, 1)
    except Exception:
        pass

    return info


def scan_and_update(audio_dir: Path, expected: list[dict]) -> dict:
    """Scan audio directory and build/update the manifest."""
    manifest_path = audio_dir / "audio_manifest.json"

    # Load existing manifest
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    # Update with expected files
    for item in expected:
        filename = item["filename"]
        file_path = audio_dir / filename
        existing = manifest.get(filename, {})

        entry = {
            "slide_id": item["slide_id"],
            "title": item["title"],
            "type": item["type"],
            "text_chars": item["text_chars"],
            "exists": file_path.exists(),
            "source": existing.get("source", "unknown"),
            "last_updated": existing.get("last_updated"),
        }

        # Get file info if it exists
        file_info = get_audio_file_info(file_path)
        if file_info:
            entry.update(file_info)
            if entry["source"] == "unknown":
                entry["source"] = "manual"
        else:
            entry["source"] = existing.get("source", "missing")

        manifest[filename] = entry

    # Check for unexpected files in the audio directory
    expected_names = {item["filename"] for item in expected}
    if audio_dir.exists():
        for f in audio_dir.glob("*.mp3"):
            if f.name not in expected_names and f.name not in manifest:
                file_info = get_audio_file_info(f) or {}
                entry = {
                    "slide_id": -1,
                    "title": "Unknown / Extra file",
                    "type": "unknown",
                    "exists": True,
                    "source": "unknown",
                }
                entry.update(file_info)
                manifest[f.name] = entry

    # Save manifest
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def print_report(manifest: dict, missing_only: bool = False):
    """Print a formatted report of the audio manifest."""
    total = len(manifest)
    existing = sum(1 for v in manifest.values() if v.get("exists"))
    missing = total - existing

    if not missing_only:
        print(f"\n{'='*60}")
        print(f"  AUDIO MANIFEST REPORT")
        print(f"{'='*60}")
        print(f"  Total expected files: {total}")
        print(f"  Existing:             {existing}")
        print(f"  Missing:              {missing}")
        print(f"{'='*60}\n")

    # Group by slide
    by_slide: dict[int, list] = {}
    for filename, info in sorted(manifest.items(), key=lambda x: x[1].get("slide_id", 99)):
        sid = info.get("slide_id", -1)
        by_slide.setdefault(sid, []).append((filename, info))

    for slide_id in sorted(by_slide.keys()):
        items = by_slide[slide_id]
        for filename, info in items:
            exists = info.get("exists", False)

            if missing_only and exists:
                continue

            status = "OK" if exists else "MISSING"
            icon = "  [OK]     " if exists else "  [MISSING]"
            duration = info.get("duration_seconds", "?")
            source = info.get("source", "?")
            size = info.get("size_kb", "?")

            print(f"{icon} Slide {slide_id:2d} | {filename:<35s} | {status} | {duration}s | {size}KB | src: {source}")

    if missing > 0:
        print(f"\n  {missing} file(s) missing. Generate with:")
        print(f"    python tools/kokoro_batch_generate.py")
        print(f"    python tools/kokoro_batch_generate.py --export-text")
    elif not missing_only:
        print(f"\n  All audio files present!")


def main():
    parser = argparse.ArgumentParser(description="Audio manifest manager")
    parser.add_argument("--config", default="config/presentation.yaml", help="Presentation config YAML")
    parser.add_argument("--audio-dir", default="frontend/audio/", help="Audio directory")
    parser.add_argument("--report", action="store_true", help="Print a summary report")
    parser.add_argument("--missing-only", action="store_true", help="Show only missing files")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    config_path = project_root / args.config
    audio_dir = project_root / args.audio_dir

    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)

    config = load_presentation_config(config_path)
    expected = get_expected_files(config)

    print(f"Scanning {audio_dir} against {len(expected)} expected files...")
    manifest = scan_and_update(audio_dir, expected)

    manifest_path = audio_dir / "audio_manifest.json"
    print(f"Manifest saved: {manifest_path}")

    if args.report or args.missing_only:
        print_report(manifest, args.missing_only)
    else:
        print_report(manifest)


if __name__ == "__main__":
    main()
