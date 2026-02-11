# Workflow: Presentation Day Runbook

## Objective
Day-of checklist and emergency procedures for the live presentation.

## Pre-Presentation (30 min before)

- [ ] Verify internet connection is stable
- [ ] Start backend: `docker-compose up -d` (or verify it's running)
- [ ] Open presenter screen on projector: `http://your-url/static/index.html`
- [ ] Open Chainlit on your laptop: `http://your-url:8001`
- [ ] Verify WebSocket connection (Chainlit shows "Connected to DexIQ backend")
- [ ] Test audio output on projector speakers
- [ ] Open Q&A page on your phone to verify it loads
- [ ] Check ElevenLabs credits: `python tools/elevenlabs_tts.py --credits`
- [ ] Have backup Bluetooth speaker ready
- [ ] Print quick reference card (see PROJECT_GUIDE.md appendix)

## Presentation Flow

1. **You speak live** — Introduce the session, then say "Take it away, DexIQ"
2. **Type `/intro`** — DexIQ introduces itself
3. **Type `/start`** — Begin slide narration
4. **Type `/next`** — After each slide narration finishes
5. **Type `/ask Name: Question`** — At interaction points
6. **Type the answer summary** — After the person responds
7. **Continue with `/next`** — Through remaining slides
8. **Type `/qa`** — Enter Q&A mode
9. **Type `/pick N`** — Select questions to answer
10. **Type `/outro`** — Closing remarks
11. **You speak live** — Thank the audience, wrap up

## Emergency Procedures

### If live TTS fails
- The response text will be displayed on screen
- Read it aloud yourself
- Continue with `/skip` and `/next`

### If LLM API fails
- Use fallback responses from `config/presentation.yaml`
- Skip audience interactions with `/skip`
- Move to next slide with `/next`

### If internet drops
- Pre-generated audio still works (it's local)
- Q&A mode won't work — say "We'll follow up after the session"
- Continue with pre-generated slides

### If everything breaks
- Take over manually — slides still work as a normal Reveal.js deck
- Navigate with keyboard (enable in browser console: `Reveal.configure({keyboard: true})`)
- Frame it as: "Looks like my AI partner needs a coffee break — let me take over"

## Quick Reference

```
/intro          → AI introduces itself
/start          → Begin slide narration
/next           → Next slide
/prev           → Previous slide
/goto N         → Jump to slide N
/ask Name: Q    → AI asks Name a question
(type answer)   → AI responds to their answer
/qa             → Enter Q&A mode
/pick N         → Answer question #N
/outro          → Closing remarks
/pause          → EMERGENCY STOP
/resume         → Continue
/status         → Check state
/skip           → Skip current action
```
