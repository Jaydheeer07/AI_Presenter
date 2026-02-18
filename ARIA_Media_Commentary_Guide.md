# ARIA Media Commentary — `/video` and `/audio` Commands
## Integration Guide for Coding Agent

> **Context:** ARIA is the AI presenter for Dexterous Group.
> This guide adds two new slash commands — `/video` and `/audio` — that trigger
> ARIA to deliver short, casual spoken commentary about the media currently playing
> on slides 9 and 10. Commentary is **pre-written and pre-recorded** (not LLM-generated),
> keeping latency at zero and ensuring the tone is exactly right.

---

## How It Works

```
Puppeteer types: /video
        ↓
Backend recognises new command type "video"
        ↓
new video_commentary_node() runs
        ↓
WebSocket sends: play_audio → slide_09_video_commentary.mp3
        ↓
ARIA speaks her commentary over the still-playing video
```

Same pattern for `/audio` → `slide_10_audio_commentary.mp3`.

The video and music keep playing underneath — commentary is a **separate audio overlay**
played through the same `<audio id="audio-player">` element.
Since it's an overlay, the existing video and music must be playing first
(puppeteer clicks Play in the slide before typing the slash command).

---

## 1. Narration Scripts

### `/video` — Seedance Clip Commentary

> **Slide context:** Slide 9 is showing an AI-generated action sequence mashing together
> Godzilla, Transformers, Iron Man, Captain America, Po from Kung Fu Panda, Pikachu —
> all in a New York cityscape — culminating in Doraemon going full god-mode with a
> glowing sword and beam of light.

---

**Option A — Casual & Funny (Recommended)**
*(~30 seconds spoken)*

```
So. What you are looking at right now.

This was not made by a film studio. There was no director, no VFX team, no
budget. Someone typed a description — something like "Godzilla vs Transformers
vs the Avengers, New York City, total chaos" — and an AI generated this.

I particularly enjoy Doraemon in there. He starts with a gun. Decides that's
not enough. Gets a halo. Pulls out a legendary sword. And single-handedly
saves the city. As you do.

This is Seedance 2.0. Released two weeks ago. Hollywood has already sent
cease-and-desist letters. I think that's the best indicator of how seriously
anyone should take this technology.
```

---

**Option B — Slightly More Informative**
*(~28 seconds spoken)*

```
What you're seeing is Seedance 2.0 — ByteDance's AI video model, released
literally two weeks ago. Someone gave it a prompt. This is what came out.

The characters are all wrong — Doraemon probably shouldn't be able to summon
a glowing sword — but look at the scale of it. The explosions, the city,
the camera movement. A visual effects team would take months to produce
this. An AI produced it from text in minutes.

Disney and Paramount have already lawyered up over this model. That should
tell you everything about where AI video is heading.
```

---

**Option C — Audience-Engaging**
*(~25 seconds spoken)*

```
I want you to clock something while you watch this.

Every single character in this video — Godzilla, Optimus Prime, Iron Man,
and yes, Doraemon in full god mode — was placed there by an AI interpreting
a text description. No animator. No artist. No studio.

Two weeks ago this model didn't exist publicly. Today, any of you can
generate something like this with a free trial. That's the pace we're
operating at.

Also, Doraemon winning the fight is extremely correct. Just wanted to say that.
```

---

**Recommended: Option A** — the Doraemon observation always lands with an audience.
Generate audio for whichever option you choose and name the file:
```
frontend/audio/slide_09_video_commentary.mp3
```

---

### `/audio` — AI Music Commentary

> **Slide context:** Slide 10 is playing an AI-generated 1970s soul-funk cover of
> "Low" by Flo Rida ft. T-Pain. The AI has flipped the original's heavy synths and
> club beats into a smooth, vintage groove with a warm bassline and soulful vocals.
> The iconic opening lyrics are clearly recognisable.

---

**Option A — Casual & Recognisable (Recommended)**
*(~28 seconds spoken)*

```
Raise your hand if you recognise this song.

That is "Low" by Flo Rida. From 2007. Except the original had none of that
warmth — it was all synths and club bass. An AI took the stems, the melody,
and the lyrics, and reimagined the whole thing as a 1970s soul-funk track.

It did that in roughly the same time it took me to say that sentence.

Tools like Suno, Udio, and Stability Audio are doing this right now — full
genre flips, cover versions, original compositions. The question for your
industry isn't whether this technology exists. It's what you do with it
before your competitors figure it out.
```

---

**Option B — Lighter & More Fun**
*(~22 seconds spoken)*

```
Apple bottom jeans. Boots with the fur. In 1970s soul-funk.

Genuinely one of my favourite things AI has produced. Someone gave a tool
called Suno a prompt — something like "Low by Flo Rida, reimagined as
70s soul" — and this came out on the first try.

The vocals are smooth, the bassline is perfect, and honestly? I prefer
this version. Don't tell Flo Rida.

The point is: AI isn't just generating functional content anymore.
It's generating genuinely surprising creative work.
```

---

**Option C — Transition Back to Business**
*(~25 seconds spoken)*

```
So that's "Low" — as it would have sounded if Flo Rida had been born in 1955.

I want to bring this back to your world for a second. Everything we're
showing you in this section — the images, the video, the music — these are
not things that required a team or a budget. They required a prompt and
about 60 seconds.

For an accounting firm, that means client-ready graphics for presentations.
Internal comms with a professional sound. Marketing material for a fraction
of the cost. The creative budget conversation is changing, and AI is
why.
```

---

**Recommended: Option B** — the "don't tell Flo Rida" line gets a laugh and keeps
the tone light before the transition into AI Safety on the next slide.
Generate audio and name the file:
```
frontend/audio/slide_10_audio_commentary.mp3
```

---

## 2. Backend Changes

### 2.1 `backend/agent/commands.py`

#### Add new commands to `VALID_COMMANDS`:

```python
# OLD
VALID_COMMANDS = {
    "intro", "start", "next", "prev", "goto", "ask", "example",
    "qa", "pick", "outro", "pause", "resume", "skip", "status",
}

# NEW
VALID_COMMANDS = {
    "intro", "start", "next", "prev", "goto", "ask", "example",
    "qa", "pick", "outro", "pause", "resume", "skip", "status",
    "video", "audio",   # ← ADD THESE TWO
}
```

No additional `parse_command` logic needed — both commands take no arguments,
so the default empty-payload path handles them correctly.

---

### 2.2 `backend/agent/states.py` (no change needed)

No new state fields required. Commentary reuses the existing `PRESENTING` / `RESPONDING`
agent state and the existing `is_audio_playing` / `current_audio_type` fields.

---

### 2.3 `backend/agent/actions.py`

#### Add two new node functions (add after `transitioning_node`):

```python
def video_commentary_node(state: GraphState) -> dict:
    """VIDEO_COMMENTARY state — ARIA comments on the Seedance video playing on slide 9."""
    logger.info("Playing video commentary for slide 9.")

    ws_messages = [
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {
            "type": "play_audio",
            "data": {
                "audioUrl": "/audio/slide_09_video_commentary.mp3",
                "audioType": "pre_generated",
            },
        },
        {"type": "status", "data": {"state": "video_commentary", "message": "ARIA is commenting on the video..."}},
    ]

    return {
        "agent_state": AgentState.PRESENTING,   # Reuse PRESENTING — no new state needed
        "is_audio_playing": True,
        "current_audio_type": AudioType.PRE_GENERATED,
        "ws_messages": ws_messages,
    }


def audio_commentary_node(state: GraphState) -> dict:
    """AUDIO_COMMENTARY state — ARIA comments on the AI music sample playing on slide 10."""
    logger.info("Playing audio commentary for slide 10.")

    ws_messages = [
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {
            "type": "play_audio",
            "data": {
                "audioUrl": "/audio/slide_10_audio_commentary.mp3",
                "audioType": "pre_generated",
            },
        },
        {"type": "status", "data": {"state": "audio_commentary", "message": "ARIA is commenting on the music..."}},
    ]

    return {
        "agent_state": AgentState.PRESENTING,   # Reuse PRESENTING
        "is_audio_playing": True,
        "current_audio_type": AudioType.PRE_GENERATED,
        "ws_messages": ws_messages,
    }
```

---

### 2.4 `backend/agent/actions.py` — `route_next_command`

Inside the `route_next_command` function, add two new `elif` branches
alongside the other command handlers:

```python
elif cmd_type == "video":
    result["agent_state"] = AgentState.PRESENTING
    # We call the node directly via graph routing — see graph.py changes below
    # Temporarily mark the command so decide_next_state routes to the right node
    result["_commentary_type"] = "video"

elif cmd_type == "audio":
    result["agent_state"] = AgentState.PRESENTING
    result["_commentary_type"] = "audio"
```

> **Simpler alternative (recommended if graph changes feel complex):**
>
> Instead of adding a new graph node, handle `/video` and `/audio` directly
> inside `route_next_command` by immediately building the `ws_messages` payload
> there — bypassing the node routing entirely. This is the zero-graph-change path:

```python
elif cmd_type == "video":
    result["agent_state"] = AgentState.PRESENTING
    result["is_audio_playing"] = True
    result["current_audio_type"] = AudioType.PRE_GENERATED
    result["ws_messages"] = [
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {
            "type": "play_audio",
            "data": {
                "audioUrl": "/audio/slide_09_video_commentary.mp3",
                "audioType": "pre_generated",
            },
        },
        {"type": "status", "data": {"state": "presenting", "message": "ARIA commenting on video..."}},
    ]

elif cmd_type == "audio":
    result["agent_state"] = AgentState.PRESENTING
    result["is_audio_playing"] = True
    result["current_audio_type"] = AudioType.PRE_GENERATED
    result["ws_messages"] = [
        {"type": "show_avatar", "data": {"mode": "speaking"}},
        {
            "type": "play_audio",
            "data": {
                "audioUrl": "/audio/slide_10_audio_commentary.mp3",
                "audioType": "pre_generated",
            },
        },
        {"type": "status", "data": {"state": "presenting", "message": "ARIA commenting on music..."}},
    ]
```

**Use this simpler path.** It's consistent with how other state transitions already
work and avoids touching `graph.py` entirely.

---

### 2.5 `config/presentation.yaml`

Add documentation entries for the two new commands at the bottom of the config
(for reference only — these don't affect the slide flow):

```yaml
# ── Media Commentary Commands ─────────────────────────────────────────────────
# These slash commands can be typed by the puppeteer at any time while on
# slides 9 or 10 to trigger ARIA's commentary. They are not part of the
# slide sequence.
#
# /video  →  plays slide_09_video_commentary.mp3 (Seedance clip commentary)
# /audio  →  plays slide_10_audio_commentary.mp3 (AI music commentary)
#
# Workflow for the puppeteer:
#   1. Navigate to slide 9 (/next)
#   2. Click "Play" button on the video tile in the browser
#   3. Wait a few seconds (let audience absorb the visuals)
#   4. Type: /video  →  ARIA speaks her commentary over the video
#   5. /next to slide 10
#   6. Click "Play" on the music player
#   7. Let it play for ~15 seconds
#   8. Type: /audio  →  ARIA speaks her commentary
#   9. /next to slide 11 (Safety)
```

---

## 3. Audio File Summary

| File | Slide | Command | Content |
|------|-------|---------|---------|
| `slide_09_video_commentary.mp3` | 9 | `/video` | ARIA's Seedance clip commentary |
| `slide_10_audio_commentary.mp3` | 10 | `/audio` | ARIA's AI music commentary |

Both files go in: `frontend/audio/`

**Record using your Kokoro TTS Docker setup.**
Use whichever Option (A/B/C) you chose from Section 1.

---

## 4. `prompts.yaml` Update (Optional)

If you want ARIA's persona to be consistent across the system prompts file,
update the header reference from DexIQ → ARIA. No functional change, just
housekeeping:

```yaml
# ARIA AI Presenter - System Prompts
# (was: DexIQ AI Presenter)

system_prompts:
  audience_response: |
    You are ARIA, an AI assistant presenting a Lunch & Learn at Dexterous Group,
    an Australian accounting firm...
    # (rest unchanged, just update the name)

  qa_answer: |
    You are ARIA, an AI assistant presenting a Lunch & Learn about AI tools
    and productivity at Dexterous Group, an Australian accounting firm...
    # (rest unchanged)
```

---

## 5. Puppeteer Workflow Reference

```
SLIDE 9 — AI Images & Video
────────────────────────────
/next               → navigate to slide 9
                    → let image carousel run for 20–30 seconds while narrating
/play audio         → type /goto 9 if needed, then click Play on video tile manually
                      (Play button is in the browser, not a slash command)
/video              → ARIA delivers Seedance commentary (~25–30 sec)
/next               → advance to slide 10


SLIDE 10 — AI Music & Creative Writing
────────────────────────────────────────
                    → click Play on music player manually in the browser
                    → let music play for 10–15 seconds
/audio              → ARIA delivers music commentary (~22–28 sec)
                    → music continues playing underneath commentary
/next               → advance to slide 11 (Safety)
```

---

## 6. Verification Checklist

- [ ] `VALID_COMMANDS` in `commands.py` includes `"video"` and `"audio"`
- [ ] `/video` typed in Chainlit → avatar enters speaking mode → `slide_09_video_commentary.mp3` plays
- [ ] `/audio` typed in Chainlit → avatar enters speaking mode → `slide_10_audio_commentary.mp3` plays
- [ ] Both commands work regardless of current slide (no slide guard needed — puppeteer is responsible)
- [ ] `/status` still returns correct state after using `/video` or `/audio`
- [ ] Music sample on slide 10 keeps playing through browser after ARIA's audio starts (they use different audio elements: `<audio id="musicSample">` vs `<audio id="audio-player">`)
- [ ] Seedance video on slide 9 keeps playing through browser after ARIA's commentary (video element is separate from the audio player)

> **Note on audio conflict:** The music player (`<audio id="musicSample">`) and the
> main audio player (`<audio id="audio-player">`) are separate DOM elements.
> When ARIA's commentary plays via the main player, the music sample should
> continue. If you find they conflict (browser audio policy), the simplest fix
> is to reduce `musicSample` volume to 40% when `audio-player` is active —
> add this logic to the `play_audio` handler in `presenter.js`:
>
> ```javascript
> // In handleMessage → play_audio case, add:
> const musicEl = document.getElementById('musicSample');
> if (musicEl && !musicEl.paused) {
>     musicEl.volume = 0.3;
>     audioPlayer.addEventListener('ended', () => { musicEl.volume = 1.0; }, { once: true });
> }
> ```

---

*ARIA Media Commentary Guide — v1.0*
*Companion to: ARIA_Presenter_Implementation_Guide.md*
