"""Configuration validator tool.

Validates presentation.yaml, audience.yaml, and prompts.yaml
to catch errors before the presentation.

Usage:
    python tools/validate_config.py
"""

import sys
from pathlib import Path

import yaml


def validate_presentation(config_path: Path) -> list[str]:
    """Validate presentation.yaml."""
    errors = []

    if not config_path.exists():
        return [f"File not found: {config_path}"]

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return ["Empty config file"]

    presentation = data.get("presentation", {})
    if not presentation.get("title"):
        errors.append("Missing presentation title")
    if not presentation.get("presenter_name"):
        errors.append("Missing presenter_name")

    slides = data.get("slides", [])
    if not slides:
        errors.append("No slides defined")
        return errors

    slide_ids = set()
    for slide in slides:
        sid = slide.get("id")
        if sid is None:
            errors.append(f"Slide missing 'id': {slide.get('title', 'unknown')}")
        elif sid in slide_ids:
            errors.append(f"Duplicate slide id: {sid}")
        slide_ids.add(sid)

        if not slide.get("title"):
            errors.append(f"Slide {sid}: missing title")

        if slide.get("narration") and not slide.get("audio_file"):
            errors.append(f"Slide {sid}: has narration but no audio_file defined")

        if slide.get("has_interaction"):
            interaction = slide.get("interaction")
            if not interaction:
                errors.append(f"Slide {sid}: has_interaction=true but no interaction config")
            elif not interaction.get("question"):
                errors.append(f"Slide {sid}: interaction missing question text")

    return errors


def validate_audience(config_path: Path) -> list[str]:
    """Validate audience.yaml."""
    errors = []

    if not config_path.exists():
        return [f"File not found: {config_path}"]

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    audience = data.get("audience", [])
    if not audience:
        errors.append("No audience members defined")
        return errors

    names = set()
    for member in audience:
        name = member.get("name")
        if not name:
            errors.append("Audience member missing name")
        elif name in names:
            errors.append(f"Duplicate audience name: {name}")
        names.add(name)

        if not member.get("question"):
            errors.append(f"{name}: missing question")

    return errors


def validate_prompts(config_path: Path) -> list[str]:
    """Validate prompts.yaml."""
    errors = []

    if not config_path.exists():
        return [f"File not found: {config_path}"]

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    prompts = data.get("system_prompts", {})
    required_prompts = ["audience_response", "qa_answer", "question_filter"]

    for key in required_prompts:
        if key not in prompts:
            errors.append(f"Missing prompt: {key}")
        elif not prompts[key].strip():
            errors.append(f"Empty prompt: {key}")

    return errors


def main():
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"

    all_errors = []

    print("Validating presentation.yaml...")
    errors = validate_presentation(config_dir / "presentation.yaml")
    all_errors.extend(errors)
    print(f"  {'PASS' if not errors else f'FAIL ({len(errors)} errors)'}")
    for e in errors:
        print(f"    - {e}")

    print("Validating audience.yaml...")
    errors = validate_audience(config_dir / "audience.yaml")
    all_errors.extend(errors)
    print(f"  {'PASS' if not errors else f'FAIL ({len(errors)} errors)'}")
    for e in errors:
        print(f"    - {e}")

    print("Validating prompts.yaml...")
    errors = validate_prompts(config_dir / "prompts.yaml")
    all_errors.extend(errors)
    print(f"  {'PASS' if not errors else f'FAIL ({len(errors)} errors)'}")
    for e in errors:
        print(f"    - {e}")

    print()
    if all_errors:
        print(f"VALIDATION FAILED: {len(all_errors)} error(s) found.")
        sys.exit(1)
    else:
        print("ALL CONFIGS VALID.")


if __name__ == "__main__":
    main()
