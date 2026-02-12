# Workflow: Generate Narration Audio

## Objective
Generate all pre-recorded narration audio files using Kokoro TTS (batch or manual via Docker UI).

## Required Inputs
- `config/presentation.yaml` — narration scripts for each slide
- Kokoro TTS (local Docker setup or Python API)

## Option A: Manual Generation via Kokoro Docker UI (Recommended)

1. **Export narration texts:**
   ```bash
   python tools/kokoro_batch_generate.py --export-text
   ```
   This creates `.txt` files in `.tmp/narration_texts/`, one per audio file.

2. **Generate in Kokoro Docker UI:**
   - Open your Kokoro Docker UI
   - For each `.txt` file, paste the text and generate audio
   - Download the MP3 and save to `frontend/audio/` with the matching filename
   - Tweak voice, speed, and pronunciation as needed

3. **Update manifest:**
   ```bash
   python tools/audio_manifest.py --report
   ```

## Option B: Batch Generation via Kokoro Python API

1. **Review narration scripts** — Open `config/presentation.yaml` and verify all narration text is finalized (remove DRAFT status).

2. **Dry run first:**
   ```bash
   python tools/kokoro_batch_generate.py --dry-run
   ```

3. **Run batch generation:**
   ```bash
   python tools/kokoro_batch_generate.py
   ```

4. **Regenerate specific slides only:**
   ```bash
   python tools/kokoro_batch_generate.py --slide 4 --slide 7
   ```

5. **Skip files you've already manually tweaked:**
   ```bash
   python tools/kokoro_batch_generate.py --skip-existing
   ```

## Post-Generation (Both Options)

1. **Listen to each file** — Play every generated MP3 and check for:
   - Pronunciation errors
   - Awkward pacing
   - Volume consistency

2. **Check manifest for missing files:**
   ```bash
   python tools/audio_manifest.py --missing-only
   ```

3. **Normalize audio levels:**
   ```bash
   python tools/audio_utils.py --normalize frontend/audio/ --target-db -20
   ```

4. **Validate all files:**
   ```bash
   python tools/audio_utils.py --check frontend/audio/
   ```

## Testing ElevenLabs Live TTS

1. **Check configuration:**
   ```bash
   python tools/elevenlabs_tts.py --status
   ```

2. **Test synthesis:**
   ```bash
   python tools/elevenlabs_tts.py --text "Hello, I'm DexIQ" --output .tmp/tts_test.mp3
   ```

3. **Test streaming mode:**
   ```bash
   python tools/elevenlabs_tts.py --text "Testing streaming" --stream
   ```

4. **Check credits:**
   ```bash
   python tools/elevenlabs_tts.py --credits
   ```

5. **Or use the REST API endpoint (when backend is running):**
   ```
   POST http://localhost:8000/api/tts/test
   {"text": "Hello, I'm DexIQ, your AI presenter."}
   ```

## Expected Output
- All `frontend/audio/*.mp3` files generated and reviewed
- `frontend/audio/audio_manifest.json` up to date
- Consistent volume levels across all files
- ElevenLabs live TTS verified working

## Edge Cases
- If Kokoro produces garbled output, try adjusting the voice parameter or rephrasing the text.
- Long narration scripts may need to be split into segments and concatenated.
- If ElevenLabs is rate-limited (429), the service will auto-retry with exponential backoff.
