# Workflow: Generate Narration Audio

## Objective
Batch-generate all pre-recorded narration audio files using Kokoro TTS.

## Required Inputs
- `config/presentation.yaml` — narration scripts for each slide
- `config/audience.yaml` — audience interaction questions
- Kokoro TTS installed locally

## Steps

1. **Review narration scripts** — Open `config/presentation.yaml` and verify all narration text is finalized (remove DRAFT status).
2. **Run batch generation:**
   ```bash
   python tools/kokoro_batch_generate.py --config config/presentation.yaml --output frontend/audio/
   ```
3. **Listen to each file** — Play every generated MP3 and check for:
   - Pronunciation errors
   - Awkward pacing
   - Volume consistency
4. **Regenerate any bad files** — Edit the narration text in the YAML and re-run for specific slides.
5. **Normalize audio levels:**
   ```bash
   python tools/audio_utils.py --normalize frontend/audio/ --target-db -20
   ```
6. **Validate all files:**
   ```bash
   python tools/audio_utils.py --check frontend/audio/
   ```
7. **Generate audience question audio** — Ensure all `/ask` question audio files exist.

## Expected Output
- All `frontend/audio/*.mp3` files generated and reviewed
- Consistent volume levels across all files

## Edge Cases
- If Kokoro produces garbled output, try adjusting the voice parameter or rephrasing the text.
- Long narration scripts may need to be split into segments and concatenated.
