"""Kokoro TTS batch generation tool.

Reads narration scripts from config/presentation.yaml and generates
MP3 audio files for each slide using Kokoro TTS (local).

Modes:
  --generate     Generate audio via Kokoro Python API (default)
  --export-text  Export narration scripts as .txt files for manual generation
                 via the Kokoro Docker UI. Each file is named to match the
                 expected audio filename so you can generate and rename easily.
  --dry-run      Show what would be generated without doing anything

Usage:
    python tools/kokoro_batch_generate.py
    python tools/kokoro_batch_generate.py --export-text --output .tmp/narration_texts/
    python tools/kokoro_batch_generate.py --skip-existing --voice af_heart
    python tools/kokoro_batch_generate.py --slide 4 --slide 7
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml


def load_presentation_config(config_path: str) -> dict:
    """Load presentation configuration from YAML."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_audio_jobs(config: dict, slide_filter: list[int] | None = None) -> list[dict]:
    """Extract all audio generation jobs from the presentation config.

    Returns a list of dicts with keys: slide_id, title, label, text, audio_filename.
    """
    jobs = []
    slides = config.get("slides", [])

    for slide in slides:
        slide_id = slide.get("id", -1)
        title = slide.get("title", "Untitled")

        if slide_filter and slide_id not in slide_filter:
            continue

        narration = slide.get("narration")
        audio_file = slide.get("audio_file")

        if narration and audio_file:
            jobs.append({
                "slide_id": slide_id,
                "title": title,
                "label": f"slide_{slide_id:02d}_narration",
                "text": narration.strip(),
                "audio_filename": Path(audio_file).name,
            })

        # Interaction question audio
        interaction = slide.get("interaction")
        if interaction:
            q_text = interaction.get("question")
            q_audio = interaction.get("question_audio")
            if q_text and q_audio:
                jobs.append({
                    "slide_id": slide_id,
                    "title": f"{title} — Interaction Q",
                    "label": f"slide_{slide_id:02d}_ask",
                    "text": q_text.strip(),
                    "audio_filename": Path(q_audio).name,
                })

    return jobs


def export_text_files(jobs: list[dict], output_dir: Path):
    """Export narration scripts as individual .txt files.

    Each file is named to match the expected audio filename so you can
    easily copy-paste into the Kokoro Docker UI and save the output
    with the matching name.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Also create a README in the export directory
    readme_lines = [
        "# Narration Text Exports for Kokoro TTS",
        f"# Generated: {datetime.now().isoformat()}",
        "#",
        "# Each .txt file contains the narration text for one audio file.",
        "# The filename matches the expected audio output filename.",
        "#",
        "# Workflow:",
        "#   1. Open your Kokoro Docker UI",
        "#   2. Paste the text from each .txt file",
        "#   3. Generate and download the audio",
        "#   4. Save/rename to frontend/audio/<matching_filename>.mp3",
        "#   5. Run: python tools/audio_manifest.py to update the manifest",
        "#",
        "# Files:",
    ]

    for job in jobs:
        txt_name = job["audio_filename"].replace(".mp3", ".txt")
        txt_path = output_dir / txt_name

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(job["text"])

        char_count = len(job["text"])
        print(f"  [OK] {txt_name} ({char_count} chars) — Slide {job['slide_id']}: {job['title']}")
        readme_lines.append(f"#   {txt_name} -> frontend/audio/{job['audio_filename']}")

    # Write README
    readme_path = output_dir / "README.txt"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(readme_lines) + "\n")

    print(f"\n  README written to: {readme_path}")


def generate_audio(text: str, output_path: str, voice: str = "af_heart",
                   kokoro_url: str = "http://localhost:8880") -> bool:
    """Generate audio from text using Kokoro TTS via OpenAI-compatible REST API.

    Calls POST /v1/audio/speech on the Kokoro Docker instance.

    Args:
        text: The narration text to synthesize.
        output_path: Path to save the output audio file.
        voice: Kokoro voice ID to use.
        kokoro_url: Base URL of the Kokoro API server (no trailing slash).

    Returns:
        True if generation succeeded, False otherwise.
    """
    import httpx

    base = kokoro_url.rstrip("/")
    url = f"{base}/v1/audio/speech"

    # Determine output format from file extension
    ext = Path(output_path).suffix.lstrip(".")
    response_format = ext if ext in ("mp3", "wav", "opus", "flac") else "mp3"

    payload = {
        "input": text,
        "voice": voice,
        "response_format": response_format,
        "speed": 1.0,
        "stream": False,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(resp.content)

            size_kb = len(resp.content) / 1024
            print(f"  [OK] Generated: {output_path} ({size_kb:.1f} KB)")
            return True

    except httpx.HTTPStatusError as e:
        print(f"  [ERROR] Kokoro API error {e.response.status_code}: {e.response.text[:200]}")
        return False
    except httpx.ConnectError:
        print(f"  [ERROR] Cannot connect to Kokoro at {base}")
        print(f"  Is Kokoro running? Check: {base}/health")
        return False
    except Exception as e:
        print(f"  [ERROR] Failed to generate {output_path}: {e}")
        return False


def update_manifest(audio_dir: Path, jobs: list[dict], results: dict[str, str]):
    """Update or create audio_manifest.json in the audio directory.

    The manifest tracks which audio files exist, their generation source,
    and status (generated, missing, manual).
    """
    manifest_path = audio_dir / "audio_manifest.json"

    # Load existing manifest if present
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    for job in jobs:
        filename = job["audio_filename"]
        file_path = audio_dir / filename
        existing = manifest.get(filename, {})

        entry = {
            "slide_id": job["slide_id"],
            "label": job["label"],
            "title": job["title"],
            "text_chars": len(job["text"]),
            "exists": file_path.exists(),
            "source": existing.get("source", "unknown"),
            "last_updated": existing.get("last_updated"),
        }

        # Update based on generation results
        result = results.get(filename)
        if result == "generated":
            entry["source"] = "kokoro-batch"
            entry["last_updated"] = datetime.now().isoformat()
        elif result == "skipped-exists":
            pass  # Keep existing metadata
        elif result == "failed":
            entry["source"] = existing.get("source", "unknown")
        elif file_path.exists() and entry["source"] == "unknown":
            entry["source"] = "manual"

        manifest[filename] = entry

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest updated: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch generate narration audio with Kokoro TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all audio files via Kokoro Python API
  python tools/kokoro_batch_generate.py

  # Export text files for manual generation via Kokoro Docker UI
  python tools/kokoro_batch_generate.py --export-text

  # Only regenerate specific slides
  python tools/kokoro_batch_generate.py --slide 4 --slide 7

  # Skip files that already exist (useful after manual tweaks)
  python tools/kokoro_batch_generate.py --skip-existing

  # Dry run — see what would be generated
  python tools/kokoro_batch_generate.py --dry-run
""",
    )
    parser.add_argument("--config", default="config/presentation.yaml", help="Presentation config YAML")
    parser.add_argument("--output", default="frontend/audio/", help="Output directory for audio files")
    parser.add_argument("--voice", default="af_heart", help="Kokoro voice ID")
    parser.add_argument("--kokoro-url", default=None,
                        help="Kokoro API URL (default: KOKORO_API_URL env or http://localhost:8880/)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated without generating")
    parser.add_argument("--export-text", action="store_true",
                        help="Export narration as .txt files for manual Kokoro Docker UI generation")
    parser.add_argument("--export-dir", default=".tmp/narration_texts/",
                        help="Directory for exported text files (default: .tmp/narration_texts/)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip audio files that already exist (preserve manual tweaks)")
    parser.add_argument("--slide", type=int, action="append", dest="slides",
                        help="Only process specific slide IDs (can be repeated: --slide 4 --slide 7)")
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
    jobs = collect_audio_jobs(config, args.slides)

    if not jobs:
        print("No audio jobs found. Check your config or --slide filter.")
        sys.exit(0)

    print(f"Found {len(jobs)} audio jobs from {config_path}")
    if args.slides:
        print(f"Filtered to slides: {args.slides}")
    print()

    # --- Export text mode ---
    if args.export_text:
        export_dir = project_root / args.export_dir
        print(f"Exporting narration texts to: {export_dir}")
        print()
        export_text_files(jobs, export_dir)
        print(f"\nDone! {len(jobs)} text files exported.")
        print(f"Use these with your Kokoro Docker UI, then place the .mp3 files in: {output_dir}")
        return

    # --- Generate mode ---
    print(f"Output directory: {output_dir}")
    print(f"Voice: {args.voice}")
    print(f"Skip existing: {args.skip_existing}")
    print()

    generated = 0
    skipped = 0
    failed = 0
    results: dict[str, str] = {}  # filename -> status

    for job in jobs:
        output_path = str(output_dir / job["audio_filename"])

        print(f"Slide {job['slide_id']} ({job['title']}):")
        print(f"  File: {job['audio_filename']}")
        print(f"  Text: {job['text'][:80]}...")

        # Skip if file exists and --skip-existing is set
        if args.skip_existing and Path(output_path).exists():
            print(f"  [SKIP] Already exists: {output_path}")
            skipped += 1
            results[job["audio_filename"]] = "skipped-exists"
            continue

        if args.dry_run:
            print(f"  [DRY RUN] Would generate: {output_path}")
            generated += 1
            results[job["audio_filename"]] = "dry-run"
            continue

        kokoro_url = args.kokoro_url or os.getenv("KOKORO_API_URL", "http://localhost:8880")
        if generate_audio(job["text"], output_path, args.voice, kokoro_url):
            generated += 1
            results[job["audio_filename"]] = "generated"
        else:
            failed += 1
            results[job["audio_filename"]] = "failed"

    print()
    print(f"Done! Generated: {generated}, Skipped: {skipped}, Failed: {failed}")

    # Update manifest (unless dry-run)
    if not args.dry_run:
        update_manifest(output_dir, jobs, results)


if __name__ == "__main__":
    main()
