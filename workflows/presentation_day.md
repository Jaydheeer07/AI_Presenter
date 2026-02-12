# Workflow: Presentation Day Runbook

> Lunch & Learn: Automations & Practical AI Tools for Everyday Work
> Presented by DexIQ — Dexterous Group | 2026

---

## 1. Pre-Show Setup (30 min before)

### Infrastructure
- [ ] Verify stable internet connection
- [ ] Start services: `docker compose up -d --build`
- [ ] Confirm backend healthy: `curl http://localhost:8000/health`
- [ ] Confirm Kokoro running (only needed if regenerating audio): `curl http://localhost:8880/health`

### Screens
- [ ] **Projector/TV** — Open `http://<server-ip>:8000/static/index.html` (presenter screen)
- [ ] **Your laptop** — Open `http://<server-ip>:8001` (Chainlit puppeteer console)
- [ ] **Your phone** — Open `http://<server-ip>:8000/static/ask.html` (verify Q&A page loads)

### Verification
- [ ] Chainlit shows: "Connected to DexIQ backend"
- [ ] Type `/status` — should return `idle`, slide 0
- [ ] Test projector audio — click the presenter screen once (required to unlock browser audio)
- [ ] Check ElevenLabs credits: `docker exec dexiq-backend python -c "from backend.services.tts_service import get_remaining_credits; import asyncio; print(asyncio.run(get_remaining_credits()))"`
- [ ] Verify Q&A page submits successfully from phone

### Physical
- [ ] Projector audio output working (or backup Bluetooth speaker connected)
- [ ] Laptop positioned where audience can't see your screen
- [ ] QR code for Q&A page ready (printed or on a second display)

---

## 2. Audience Roster

Update `config/audience.yaml` with actual attendees before the session.
Pre-assign who gets asked which question on which slide.

| Slide | Target | Question |
|-------|--------|----------|
| 2 | TBD | What's one task in your week that feels repetitive or draining? |
| 3 | TBD | Have you ever tried an AI tool and been surprised by how wrong it was? |
| 4 | TBD | Do you use ChatGPT already? What's your go-to use case? |
| 5 | TBD | Which ecosystem does your team primarily use — Microsoft, Google, or a mix? |
| 6 | TBD | Have you automated any part of your workflow, even something simple? |
| 7 | TBD | Has anyone here tried using AI for a personal creative project? |

---

## 3. Live Presentation Flow

### Act 1: Opening (Slides 0-1)

| Step | You Do | You Type |
|------|--------|----------|
| 1 | Greet the audience, introduce the session | *(speak live)* |
| 2 | Say "Take it away, DexIQ" | `/intro` |
| 3 | Wait for intro audio to finish | *(auto)* |

### Act 2: Content (Slides 2-8)

For each slide, the pattern is:

| Step | You Type | What Happens |
|------|----------|--------------|
| 1 | `/next` | Advances slide, plays narration audio |
| 2 | *(wait for audio to finish)* | Avatar pulses, then goes idle |
| 3 | `/ask Name: Question` | Shows question overlay, plays question audio |
| 4 | *(wait for person to answer)* | Avatar shows "listening" mode |
| 5 | `Maria says she uses ChatGPT for emails` | AI generates + speaks a live response |
| 6 | *(wait for response audio)* | Then ready for next slide |

**Slides without interaction** (slide 8: Safety) — just `/next` and wait.

**Detailed slide-by-slide:**

```
/next                                          → Slide 2: Why We're Here
/ask Name: What's one task that feels repetitive?
(type their answer summary)
/next                                          → Slide 3: What AI Is
/ask Name: Ever been surprised by how wrong AI was?
(type their answer summary)
/next                                          → Slide 4: ChatGPT
/ask Name: Do you use ChatGPT? Go-to use case?
(type their answer summary)
/next                                          → Slide 5: Ecosystem
/ask Name: Microsoft, Google, or a mix?
(type their answer summary)
/next                                          → Slide 6: Advanced Workflows
/ask Name: Automated any part of your workflow?
(type their answer summary)
/next                                          → Slide 7: Entertainment
/ask Name: Tried AI for a creative project?
(type their answer summary)
/next                                          → Slide 8: Safety (no interaction)
```

### Act 3: Q&A (Slide 9)

| Step | You Type | What Happens |
|------|----------|--------------|
| 1 | `/qa` | Goes to Q&A slide, plays intro audio |
| 2 | *(wait for questions to come in)* | Questions appear in Chainlit with scores |
| 3 | `/pick 1` | AI answers question #1 live (Claude + ElevenLabs) |
| 4 | `/pick 3` | AI answers question #3 live |
| 5 | *(repeat as time allows)* | System returns to Q&A mode after each answer |

### Act 4: Closing (Slide 10)

| Step | You Type | What Happens |
|------|----------|--------------|
| 1 | `/outro` | DexIQ delivers closing remarks |
| 2 | *(wait for audio)* | State becomes "done" |
| 3 | *(speak live)* | Thank the audience, wrap up |

---

## 4. Emergency Procedures

### Live TTS fails (ElevenLabs down)
- Response text still appears on the presenter screen
- Read it aloud yourself, then `/skip` and continue

### LLM API fails (OpenAI down)
- Fallback responses auto-generated (generic but safe)
- Skip audience interactions: `/skip` then `/next`

### Internet drops mid-presentation
- **Pre-generated audio still works** — it's served locally
- Q&A and live responses won't work
- Say: "We'll save questions for after the session"
- Continue with `/next` through remaining slides

### Audio won't play on projector
- Check browser tab isn't muted
- Click the presenter screen (browser requires user interaction to unlock audio)
- Try: open browser console → `document.getElementById('audio-player').play()`
- Last resort: backup Bluetooth speaker

### Total system failure
- Slides still work as a static Reveal.js deck
- Enable keyboard: open browser console → `Reveal.configure({keyboard: true})`
- Navigate with arrow keys, narrate slides yourself
- Frame it: "Looks like my AI partner needs a coffee break — let me take over"

### Awkward audience silence
- If no one answers the question, wait 5 seconds then type:
  `They didn't have a specific answer but seemed interested`
- DexIQ will generate a graceful transition response

---

## 5. Quick Command Reference

```
/intro              AI introduces itself (slide 1)
/start              Begin narration (slide 2)
/next               Next slide + narration
/prev               Previous slide
/goto N             Jump to slide N
/ask Name: Q        AI asks Name a question
(free text)         Summarize their answer → AI responds live
/qa                 Enter Q&A mode (slide 9)
/pick N             Answer submitted question #N
/outro              Closing remarks (slide 10)
/pause              EMERGENCY STOP — freezes everything
/resume             Continue from pause
/skip               Skip current action
/status             Check current state + slide
```

---

## 6. Post-Presentation

- [ ] Save Chainlit chat log (screenshot or export)
- [ ] Note any issues for next time
- [ ] Check ElevenLabs credit usage
- [ ] `docker compose down` when done
