# Workflow: Pre-Presentation Rehearsal

## Objective
Full dry run of the presentation to catch issues before the live event.

## Required Inputs
- Application deployed and running (local or remote)
- All audio files generated
- Audience roster populated in `config/audience.yaml`

## Checklist

### Audio
- [ ] All slide narration audio files play correctly
- [ ] All audience question audio files play correctly
- [ ] Volume levels are consistent across all files
- [ ] Live TTS (ElevenLabs) generates audio within 5 seconds

### Commands
- [ ] `/intro` plays intro audio and shows slide 1
- [ ] `/start` begins slide 2 narration
- [ ] `/next` advances slides correctly
- [ ] `/prev` goes back correctly
- [ ] `/goto N` jumps to correct slide
- [ ] `/ask Name: Question` plays question audio and shows overlay
- [ ] Free text answer triggers live LLM + TTS response
- [ ] `/qa` enters Q&A mode
- [ ] `/pick N` answers a specific question
- [ ] `/outro` plays closing remarks
- [ ] `/pause` stops everything immediately
- [ ] `/resume` continues from paused state
- [ ] `/skip` skips current action
- [ ] `/status` shows correct state info

### Frontend
- [ ] Slides display correctly on projector resolution
- [ ] Avatar pulsates when audio plays
- [ ] Avatar shows thinking animation during live generation
- [ ] Question overlay appears and disappears correctly
- [ ] Q&A page works on mobile phones

### Timing
- [ ] Total presentation fits within time slot
- [ ] Transitions between slides feel natural
- [ ] Live response latency is acceptable (< 5 seconds)

## Steps

1. Open presenter screen on projector/external monitor
2. Open Chainlit on your laptop
3. Open Q&A page on your phone
4. Run through entire presentation using slash commands
5. Have someone submit test questions via Q&A page
6. Note any issues and fix before presentation day
