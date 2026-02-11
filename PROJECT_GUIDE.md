# Project Guide: DexIQ AI Presenter

> An AI-powered presentation system where an autonomous AI assistant delivers a Lunch & Learn session about AI tools and productivity — narrating slides, interacting with audience members by name, answering live Q&A, and being orchestrated in real-time by a human puppeteer through slash commands.

---

## Table of Contents

- [1. Project Vision](#1-project-vision)
- [2. Architecture Overview](#2-architecture-overview)
- [3. Tech Stack](#3-tech-stack)
- [4. WAT Framework Integration](#4-wat-framework-integration)
- [5. System Design: The Puppet Theater](#5-system-design-the-puppet-theater)
- [6. Slash Command System](#6-slash-command-system)
- [7. State Machine (LangGraph)](#7-state-machine-langgraph)
- [8. Audio Strategy](#8-audio-strategy)
- [9. Frontend: Reveal.js Presenter Screen](#9-frontend-revealjs-presenter-screen)
- [10. Audience Q&A System](#10-audience-qa-system)
- [11. AI Avatar & Visuals](#11-ai-avatar--visuals)
- [12. Presentation Content](#12-presentation-content)
- [13. Deployment Plan](#13-deployment-plan)
- [14. Development Phases & Timeline](#14-development-phases--timeline)
- [15. Development Environment & Tooling](#15-development-environment--tooling)
- [16. Risk & Fallback Matrix](#16-risk--fallback-matrix)
- [17. Budget Estimate](#17-budget-estimate)

---

## 1. Project Vision

### What We're Building

A meta-demonstration: an AI assistant presents a Lunch & Learn about AI tools and productivity *to prove the point that AI is already this capable*. The presentation itself becomes the proof.

### The Illusion

The audience sees an autonomous AI presenter that:

- Introduces itself and explains its purpose
- Narrates and explains slides with natural-sounding speech
- Calls audience members by name and asks them questions
- Responds to their answers with personalized, contextual replies
- Answers live Q&A questions submitted by the audience
- Delivers a personalized outro

What the audience doesn't see: you, sitting with a laptop, orchestrating the entire performance through a chat interface with slash commands. You are the invisible puppeteer. The AI is the puppet that appears alive.

### Why This Approach Works

- **90% pre-generated, 10% live** — the live moments (audience interaction, Q&A) are what create the illusion of autonomy
- **Human-in-the-loop safety** — you control the pacing, select questions, and can intervene at any point
- **Graceful degradation** — if live TTS fails, pre-generated audio still works; if the API goes down, you can take over narration manually
- **Low cost, high impact** — total project cost under $20

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     YOUR CONTROL INTERFACE                        │
│                   (Chainlit Chat Interface)                        │
│                                                                    │
│  You type:                                                         │
│  > /intro                                                          │
│  > /start                                                          │
│  > /ask Maria: What AI tools do you use daily?                     │
│  > Maria says she uses ChatGPT for emails and Canva for graphics   │
│  > /next                                                           │
│  > /qa                                                             │
│  > /outro                                                          │
└─────────────────────────────┬────────────────────────────────────────┘
                              │ WebSocket
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FASTAPI + LANGGRAPH                           │
│                    (The Agent's Brain)                             │
│                                                                    │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │ Command      │  │ State Machine  │  │ Action Executor      │  │
│  │ Queue (FIFO) │  │                │  │                      │  │
│  │              │  │ IDLE           │  │ • Play pre-gen audio │  │
│  │ /ask Maria   │  │ INTRODUCING    │  │ • Call Claude API    │  │
│  │ /next        │  │ PRESENTING     │  │ • Call ElevenLabs    │  │
│  │ (queued)     │  │ ASKING         │  │ • Advance slide      │  │
│  │              │  │ RESPONDING     │  │ • Update avatar      │  │
│  │              │  │ QA_MODE        │  │ • Show visuals       │  │
│  │              │  │ OUTRO          │  │                      │  │
│  └──────────────┘  └────────────────┘  └──────────────────────┘  │
│                                                                    │
│  Context: Presentation script, audience roster, slide state,       │
│           conversation history, Q&A question pool                  │
└─────────────────────────────┬────────────────────────────────────────┘
                              │ WebSocket
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     PRESENTER SCREEN                              │
│                   (Reveal.js + Avatar)                             │
│                                                                    │
│  ┌──────────────────────────────┐  ┌───────────────────────────┐ │
│  │                              │  │      ╭──────────────╮     │ │
│  │        SLIDE CONTENT         │  │      │    ◉  AI     │     │ │
│  │     (Reveal.js slides)       │  │      │   Avatar     │     │ │
│  │                              │  │      ╰──────────────╯     │ │
│  │                              │  │  (pulsates when speaking) │ │
│  │                              │  │  (shows face on interact) │ │
│  └──────────────────────────────┘  └───────────────────────────┘ │
│                                                                    │
│  🔊 Audio output (pre-generated or live TTS)                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     AUDIENCE PHONES                               │
│                   (Q&A Submission Page)                            │
│                                                                    │
│  Scan QR code → yourapp.com/ask                                    │
│  ┌─────────────────────────┐                                      │
│  │  Type your question:    │                                      │
│  │  [____________________] │                                      │
│  │        [Submit]         │                                      │
│  │                         │                                      │
│  │  "Thanks! We'll get     │                                      │
│  │   to your question."    │                                      │
│  └─────────────────────────┘                                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack

### Core Stack

| Component | Technology | Purpose |
|---|---|---|
| Backend framework | **FastAPI** | API server, WebSocket handling, orchestration |
| Agent orchestration | **LangGraph** | State machine, command queue, agent workflow |
| Control interface | **Chainlit** | Chat UI for slash commands (your puppeteer console) |
| Slide deck | **Reveal.js** | Web-based presentation with programmatic control |
| AI brain | **Claude API** (Anthropic) or **OpenAI GPT-4o** | Generating live responses for audience interaction and Q&A |
| Pre-gen TTS | **Kokoro TTS** (local) | Generating narration audio files before the presentation |
| Live TTS | **ElevenLabs API** (free tier or $5 Starter) | Real-time speech synthesis for live responses during Q&A |
| Real-time comms | **WebSockets** (via FastAPI) | Connecting backend to presenter screen and control interface |

### Supporting Technologies

| Component | Technology | Purpose |
|---|---|---|
| Hosting | **DigitalOcean** (App Platform or Droplet) | Deployment |
| Containerization | **Docker** | Consistent deployment |
| QR code | **qrcode** (Python library) or static image | Audience Q&A access |
| Audio visualization | **Web Audio API + Canvas/CSS** | AI avatar pulsation effect |
| Task queue | **In-memory FIFO** (or Redis if needed) | Command queue management |

### What We're NOT Using (And Why)

| Skipped | Reason |
|---|---|
| NVIDIA PersonaPlex | 7B params, requires A100 GPUs — overkill for narration |
| Chatterbox / F5-TTS | Require GPU for reasonable latency |
| Whisper STT | Not needed — audience submits text, not voice |
| HeyGen / D-ID avatars | Too complex, too expensive for this scope |
| Telegram / WhatsApp bots | Unnecessary friction — simple web form is better |
| MS Teams bot | Requires Azure registration, IT approval, Bot Framework setup |

---

## 4. WAT Framework Integration

The existing WAT (Workflows, Agents, Tools) architecture from `CLAUDE.md` integrates naturally with this project. The philosophy is the same: **probabilistic AI handles reasoning, deterministic code handles execution.**

### How WAT Maps to This Project

| WAT Layer | In This Project |
|---|---|
| **Workflows** (`workflows/`) | Markdown SOPs for each phase: audio generation, deployment, presentation rehearsal |
| **Agents** (AI decision-maker) | LangGraph state machine — reads commands, decides actions, coordinates tools |
| **Tools** (`tools/`) | Python scripts for: Kokoro batch TTS generation, ElevenLabs API calls, slide config validation, QR code generation, audio file management |

### Directory Structure (WAT-Compatible)

```
ai-presenter/
├── CLAUDE.md                    # Agent instructions (WAT framework)
├── PROJECT_GUIDE.md             # This document
├── .env                         # API keys (Claude/OpenAI, ElevenLabs)
├── .env.example                 # Template for .env
├── docker-compose.yml           # Container orchestration
├── Dockerfile                   # Backend container
│
├── workflows/                   # WAT Layer 1: Markdown SOPs
│   ├── generate_audio.md        # How to batch-generate narration with Kokoro
│   ├── deploy.md                # Deployment steps for DigitalOcean
│   ├── rehearsal.md             # Pre-presentation checklist and testing
│   └── presentation_day.md     # Day-of runbook and emergency procedures
│
├── tools/                       # WAT Layer 3: Deterministic scripts
│   ├── kokoro_batch_generate.py # Reads config, generates all slide audio
│   ├── elevenlabs_tts.py        # ElevenLabs API wrapper for live TTS
│   ├── validate_config.py       # Validates presentation config YAML
│   ├── generate_qr.py           # Generates QR code for audience Q&A URL
│   └── audio_utils.py           # Audio format conversion, normalization
│
├── backend/                     # FastAPI application
│   ├── main.py                  # FastAPI app entry point
│   ├── agent/                   # LangGraph state machine
│   │   ├── graph.py             # State machine definition
│   │   ├── states.py            # State enums and models
│   │   ├── commands.py          # Slash command parser and queue
│   │   └── actions.py           # Action executors (play audio, call LLM, etc.)
│   ├── routers/
│   │   ├── presenter.py         # WebSocket for presenter screen
│   │   ├── control.py           # WebSocket/REST for Chainlit commands
│   │   └── audience.py          # REST endpoints for Q&A submissions
│   ├── services/
│   │   ├── llm_service.py       # Claude/OpenAI API integration
│   │   ├── tts_service.py       # ElevenLabs live TTS
│   │   └── question_manager.py  # Q&A question queue and filtering
│   └── models/
│       ├── presentation.py      # Pydantic models for slides, config
│       └── questions.py         # Pydantic models for Q&A
│
├── frontend/                    # Reveal.js presenter screen
│   ├── index.html               # Main presentation page
│   ├── ask.html                 # Audience Q&A submission page
│   ├── moderate.html            # (Optional) Moderator dashboard
│   ├── css/
│   │   ├── theme.css            # Presentation theme
│   │   └── avatar.css           # AI avatar animations
│   ├── js/
│   │   ├── presenter.js         # WebSocket client, slide control, audio playback
│   │   ├── avatar.js            # Audio-reactive visualization
│   │   ├── ask.js               # Q&A form submission logic
│   │   └── moderate.js          # (Optional) Moderator dashboard logic
│   └── audio/                   # Pre-generated narration files
│       ├── slide_intro.mp3
│       ├── slide_01_why_were_here.mp3
│       ├── slide_02_what_ai_is.mp3
│       ├── ...
│       ├── ask_maria_tools.mp3
│       ├── ask_jake_it.mp3
│       └── outro.mp3
│
├── config/                      # Presentation configuration
│   ├── presentation.yaml        # Slide deck config (content, narration, timing)
│   ├── audience.yaml            # Audience roster and pre-planned questions
│   └── prompts.yaml             # System prompts for Claude (Q&A, responses)
│
├── .tmp/                        # WAT temporary files (disposable)
│   └── ...
│
└── tests/
    ├── test_commands.py          # Slash command parsing tests
    ├── test_state_machine.py     # State transition tests
    └── test_queue.py             # Command queue behavior tests
```

### WAT Compatibility Notes

- **No conflicts** with the existing WAT architecture. The project extends it naturally.
- `workflows/` will contain SOPs for recurring tasks (audio generation, deployment, rehearsal).
- `tools/` will contain standalone Python scripts that Claude Code can execute independently.
- The `backend/` directory is the application code itself — not a "tool" in the WAT sense, but the product being built.
- `.env` remains the single source of truth for secrets.
- `.tmp/` is used for intermediate audio processing files.
- The self-improvement loop from WAT applies: when something breaks during rehearsal, update the relevant workflow.

---

## 5. System Design: The Puppet Theater

### Core Concept

You are the puppeteer. The AI is the puppet. The audience sees a live AI presenter. In reality, you control every transition, every interaction, and every moment through a chat interface. The AI handles the execution (speaking, responding, generating answers) but you decide *when* and *what*.

### The Three Screens

**Screen 1 — Presenter Screen (audience-facing):** Projected on the big screen. Shows Reveal.js slides, plays audio, displays the AI avatar animation. This is all the audience sees.

**Screen 2 — Your Control Console (your laptop):** Chainlit chat interface. You type slash commands to control the AI. Only you can see this. This is where you send `/start`, `/next`, `/ask`, etc.

**Screen 3 — Audience Phones:** Each audience member's phone. They scan a QR code to access a simple web page where they can submit Q&A questions.

### Communication Flow

```
You (Chainlit) ──WebSocket──► FastAPI Backend ──WebSocket──► Presenter Screen
                                    │
                                    ├──► Claude API (live responses)
                                    ├──► ElevenLabs API (live TTS)
                                    │
Audience Phones ──HTTP POST──► FastAPI Backend (question queue)
```

---

## 6. Slash Command System

### Command Reference

| Command | Syntax | Behavior | Audio Type |
|---|---|---|---|
| `/intro` | `/intro` | AI introduces itself, states purpose and goals | Pre-generated or live |
| `/start` | `/start` | Begin slide 1 narration | Pre-generated |
| `/next` | `/next` | Advance to next slide and narrate | Pre-generated |
| `/prev` | `/prev` | Go back to previous slide and narrate | Pre-generated |
| `/goto` | `/goto 5` | Jump to specific slide number | Pre-generated |
| `/ask` | `/ask Maria: What AI tools do you use?` | AI asks a specific audience member a question | Pre-generated |
| (free text) | `Maria says she uses ChatGPT for emails` | You summarize the person's answer; AI generates personalized response | **Live** (Claude + ElevenLabs) |
| `/example` | `/example` | AI provides a relevant example for the current slide | Pre-generated or live |
| `/qa` | `/qa` | Switch to Q&A mode; start answering audience-submitted questions | Live |
| `/pick` | `/pick 3` | Select a specific audience question by ID to answer | Live |
| `/outro` | `/outro` | AI delivers closing remarks | Pre-generated or live |
| `/pause` | `/pause` | Immediately pause all activity (emergency) | N/A |
| `/resume` | `/resume` | Resume from where it paused | N/A |
| `/skip` | `/skip` | Skip current action, move to next in queue | N/A |
| `/status` | `/status` | Show current state, queue contents, slide number | N/A |

### Command Queue Behavior

Commands do NOT execute immediately. They enter a FIFO (first-in, first-out) queue. The agent processes the next command only after completing its current action. This prevents abrupt interruptions.

**Exception:** `/pause` and `/stop` are interrupt commands that execute immediately regardless of queue state.

**Example scenario:**
1. AI is narrating slide 3 (state: PRESENTING)
2. You type `/ask Maria: What tools do you use?`
3. Command enters queue, does NOT interrupt current narration
4. Slide 3 narration finishes
5. Agent checks queue, finds `/ask Maria`
6. Transitions to ASKING state, plays the question audio
7. You type Maria's answer summary
8. Agent transitions to RESPONDING, generates live response
9. Response finishes, agent checks queue — empty, so auto-advances to next slide

### Queue Data Model

```python
@dataclass
class Command:
    type: str           # "intro", "start", "next", "ask", "qa", etc.
    payload: dict       # Additional data (name, question, slide_number, etc.)
    timestamp: datetime
    priority: int       # 0 = normal, 1 = interrupt (pause/stop)

class CommandQueue:
    queue: deque[Command]
    current_action: Optional[Command]
    is_busy: bool

    def enqueue(self, command: Command):
        if command.priority == 1:  # Interrupt
            self.interrupt(command)
        else:
            self.queue.append(command)
            if not self.is_busy:
                self.process_next()

    def on_action_complete(self):
        self.is_busy = False
        self.process_next()

    def process_next(self):
        if self.queue:
            cmd = self.queue.popleft()
            self.is_busy = True
            self.execute(cmd)
```

---

## 7. State Machine (LangGraph)

### States

```python
class AgentState(str, Enum):
    IDLE = "idle"                # Waiting for first command
    INTRODUCING = "introducing"  # AI delivering introduction
    PRESENTING = "presenting"    # Narrating a slide (pre-gen audio)
    ASKING = "asking"            # Asking audience member a question
    WAITING_ANSWER = "waiting"   # Waiting for puppeteer to type answer summary
    RESPONDING = "responding"    # AI generating live response to answer
    TRANSITIONING = "transitioning"  # Brief pause between states
    QA_MODE = "qa_mode"          # Answering audience-submitted questions
    OUTRO = "outro"              # Delivering closing remarks
    PAUSED = "paused"            # Emergency pause
    DONE = "done"                # Presentation complete
```

### State Transition Diagram

```
              /intro
                │
                ▼
          ┌───────────┐
          │   IDLE     │
          └─────┬─────┘
                │ /intro
                ▼
          ┌───────────────┐
          │  INTRODUCING   │──── pre-gen or live intro audio
          └───────┬───────┘
                  │ /start (or auto after intro completes)
                  ▼
    ┌────►┌───────────────┐
    │     │  PRESENTING    │──── plays slide narration (pre-gen)
    │     └───────┬───────┘
    │             │
    │     ┌───────┴─────────────────────────┐
    │     │                                 │
    │     ▼ /next                     ▼ /ask [name]: [question]
    │  (advance slide)          ┌───────────────┐
    │     │                     │   ASKING       │──── plays question audio
    │     │                     └───────┬───────┘
    │     │                             │ (auto → waiting)
    │     │                     ┌───────────────────┐
    │     │                     │  WAITING_ANSWER    │──── waiting for your input
    │     │                     └───────┬───────────┘
    │     │                             │ (you type answer summary)
    │     │                     ┌───────────────┐
    │     │                     │  RESPONDING    │──── Claude + live TTS
    │     │                     └───────┬───────┘
    │     │                             │ (auto → presenting or next in queue)
    │     └─────────────────────────────┘
    │             │
    └─────────────┘
                  │ /qa
                  ▼
          ┌───────────────┐
          │   QA_MODE      │──── reads audience questions, Claude + live TTS
          └───────┬───────┘
                  │ /outro
                  ▼
          ┌───────────────┐
          │    OUTRO       │──── pre-gen or live outro
          └───────┬───────┘
                  │ (auto)
                  ▼
          ┌───────────────┐
          │     DONE       │
          └───────────────┘

    ───── /pause from ANY state ────►  PAUSED  ────► /resume back to previous state
```

### LangGraph Node Design

Each state corresponds to a LangGraph node. The graph routes between nodes based on the current state and the next command in the queue.

```python
# Simplified LangGraph structure
from langgraph.graph import StateGraph, END

graph = StateGraph(PresentationState)

graph.add_node("idle", idle_node)
graph.add_node("introducing", introducing_node)
graph.add_node("presenting", presenting_node)
graph.add_node("asking", asking_node)
graph.add_node("waiting_answer", waiting_answer_node)
graph.add_node("responding", responding_node)
graph.add_node("qa_mode", qa_mode_node)
graph.add_node("outro", outro_node)
graph.add_node("router", route_next_command)  # Checks queue, decides next state

graph.add_edge("introducing", "router")
graph.add_edge("presenting", "router")
graph.add_edge("responding", "router")
graph.add_edge("outro", END)

graph.add_conditional_edges("router", decide_next_state, {
    "presenting": "presenting",
    "asking": "asking",
    "qa_mode": "qa_mode",
    "outro": "outro",
    "idle": "idle",
})
```

---

## 8. Audio Strategy

### Two-Tier Audio System

| Tier | When | Source | Latency | Quality Control |
|---|---|---|---|---|
| **Pre-generated** | Slide narration, planned audience questions, intro, outro | Kokoro TTS (local PC) | Zero (static files) | You review and approve every file |
| **Live** | Responses to audience answers, Q&A answers, ad-lib moments | ElevenLabs API | ~2-4 seconds | AI-generated, no preview |

### Pre-Generation Workflow (Kokoro TTS)

Run on your local PC before the presentation:

1. Write narration scripts in `config/presentation.yaml`
2. Run `tools/kokoro_batch_generate.py` which reads the config and generates `.mp3` files
3. Listen to each file, regenerate any that sound off
4. Place finalized files in `frontend/audio/`
5. Deploy with the application

```bash
# Example usage
python tools/kokoro_batch_generate.py --config config/presentation.yaml --output frontend/audio/
```

### Live TTS Workflow (ElevenLabs)

Used only during the presentation for live responses:

1. Claude API generates text response (~1-2s)
2. Text sent to ElevenLabs TTS API (~1-2s)
3. Audio streamed to presenter screen via WebSocket
4. Total latency: ~3-5 seconds (acceptable — "AI is thinking")

### Voice Consistency Strategy

Kokoro and ElevenLabs will sound different. Three options:

**Option A — Use ElevenLabs for everything.** Pre-generate all audio via ElevenLabs API too. Consistent voice, but costs credits.

**Option B — Use Kokoro for everything.** Deploy Kokoro on server for live TTS too. Consistent voice, but 1-3s latency on CPU.

**Option C — Lean into it (recommended).** During the intro, the AI says: *"You might notice my voice shifts slightly when I'm speaking off-script versus reading my prepared notes — that's me switching between presentation mode and conversation mode."* This turns the inconsistency into a feature that makes the AI seem more sophisticated.

### ElevenLabs Budget Calculation

| Usage | Estimated Credits |
|---|---|
| Development/testing | ~5,000 credits |
| Live Q&A (10-15 answers × 30-60s each) | ~8,000-12,000 credits |
| Audience interaction responses (5-8 responses) | ~3,000-5,000 credits |
| **Total estimate** | **~16,000-22,000 credits** |

Free tier: 10,000-20,000 credits/month (sources vary). Starter plan ($5/month): 30,000 credits. **Recommendation:** Start with free tier, upgrade to Starter if needed. Use Kokoro locally for all development testing to conserve ElevenLabs credits.

---

## 9. Frontend: Reveal.js Presenter Screen

### Presentation Layout

The presenter screen has two main layouts:

**Layout A — Slide Focus (during narration):**
Slides fill most of the screen. A small audio waveform/avatar indicator sits in the bottom-right corner, pulsating when the AI speaks.

**Layout B — Interaction Focus (during audience interaction and Q&A):**
Slides shrink or move to the side. The AI avatar becomes more prominent. The question text is displayed on screen for the audience to read.

### Reveal.js Configuration

Slides are defined in HTML but controlled programmatically by the backend via WebSocket commands:

```javascript
// Frontend receives commands from backend
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    switch (data.type) {
        case 'advance_slide':
            Reveal.next();
            break;
        case 'goto_slide':
            Reveal.slide(data.slideIndex);
            break;
        case 'play_audio':
            playAudio(data.audioUrl);
            break;
        case 'show_question':
            displayQuestion(data.question, data.targetName);
            break;
        case 'show_avatar':
            toggleAvatar(true);
            break;
        case 'hide_avatar':
            toggleAvatar(false);
            break;
    }
};
```

### Slide Content Preparation

You do NOT need to finalize the Reveal.js HTML now. The content should be prepared in `config/presentation.yaml` first (see Section 12), and the Reveal.js slides can be generated from that config during development. What you need now is the content and narration scripts.

---

## 10. Audience Q&A System

### How It Works

1. A slide during the presentation displays a QR code and short URL
2. Audience members scan with their phones → opens `/ask` page
3. They type a question and submit
4. Questions flow into the backend's question queue
5. During Q&A mode, you (or the AI auto-filter) select which questions to answer
6. AI generates answer via Claude API → ElevenLabs TTS → played on presenter screen

### Question Filtering (Auto + Manual)

The backend can auto-filter questions using Claude:

```
System prompt: "You are moderating Q&A for a presentation about AI productivity tools
at an accounting firm. Score this question 1-10 on relevance. Flag if off-topic,
inappropriate, or duplicate. Return JSON: {score: int, flag: str|null, reason: str}"
```

High-scoring questions auto-queue. Flagged questions go to your moderator view. You can manually `/pick` any question.

### Q&A Page Design

Minimal, mobile-optimized, no login required:

```
┌─────────────────────────┐
│  🤖 Ask a Question       │
│                          │
│  Your name (optional):   │
│  [____________________]  │
│                          │
│  Your question:          │
│  [____________________]  │
│  [____________________]  │
│                          │
│       [Submit]           │
│                          │
│  ✅ Submitted! We'll     │
│  address your question   │
│  during Q&A.             │
└─────────────────────────┘
```

---

## 11. AI Avatar & Visuals

### Recommended Approach: Audio-Reactive Waveform + Conditional Face

**During slide narration:** Show a small audio-reactive waveform (circle or bars) in the corner that pulses with the AI's voice. The avatar is minimal — it's there to show the AI is "speaking" but doesn't distract from the slides.

**During interactions (intro, asking questions, Q&A):** The avatar becomes more prominent. If pre-generated, you could use an AI-generated face video with lip-sync. If live, show the waveform only (since lip-sync can't be generated in real-time).

### Implementation: Web Audio API

```javascript
// Audio-reactive visualization (conceptual)
const audioContext = new AudioContext();
const analyser = audioContext.createAnalyser();
const source = audioContext.createMediaElementSource(audioElement);
source.connect(analyser);
analyser.connect(audioContext.destination);

function animate() {
    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(data);
    const average = data.reduce((a, b) => a + b) / data.length;

    // Use 'average' to control avatar size/opacity/color
    avatar.style.transform = `scale(${1 + average / 512})`;
    requestAnimationFrame(animate);
}
```

### Avatar States

| State | Visual |
|---|---|
| Idle | Gentle slow pulse, dim color |
| Speaking (pre-gen) | Active pulse synced to audio, bright color |
| Speaking (live) | Active pulse synced to audio, slightly different color (conversation mode) |
| Thinking | Spinning/loading animation (while Claude generates response) |
| Listening | Subtle breathing animation, different color |

---

## 12. Presentation Content

### Source Material

Based on the uploaded `Presentation_Sample.txt`, the Lunch & Learn covers:

1. Introduction: Why We're Here
2. Setting the Stage: What AI Is (and Isn't)
3. Core Productivity: ChatGPT
4. Ecosystem Comparison: Copilot vs. Gemini
5. Advanced Workflows & Technical Efficiency
6. Bonus: AI for Entertainment & Creative Leisure
7. Closing: AI Safety & Good Habits

### Enhanced Slide Deck (For AI Presenter)

The following is an expanded version of your presentation, restructured for the AI presenter format. Each slide includes visual content (what's on screen), narration script (what the AI says), and interaction cues.

---

#### Slide 0: Title Slide

**On screen:**
> **Lunch & Learn: Automations & Practical AI Tools for Everyday Work**
> Presented by DexIQ — Your AI Assistant
> Dexterous Group | 2026

**Narration:** *(None — you deliver the human intro yourself)*

**Your live intro (you speak):** "Good morning/afternoon everyone. Thanks for joining today's Lunch & Learn. As you know, today's topic is AI tools for everyday work. And I thought — what better way to talk about AI than to have an AI do the talking? So I'd like to introduce my colleague and co-presenter who will be guiding us through today's session. Take it away, DexIQ."

**Trigger:** You type `/intro` in Chainlit.

---

#### Slide 1: AI Introduction

**On screen:**
> **"Hello, Dexterous!"**
> 🤖 DexIQ — AI Assistant
> *"I'm here to walk you through how AI tools can make your work easier — and maybe even more fun."*

**Narration (pre-gen or live):**
"Hello everyone! I'm DexIQ, an AI assistant, and I'll be your presenter today. My goal is simple: I want to show you practical, real-world ways that AI tools can help you work smarter — whether that's drafting emails faster, automating repetitive tasks, or even exploring creative side projects. I'll also be asking some of you questions throughout the session, so stay sharp! And toward the end, you'll have a chance to ask me anything. Just scan the QR code when we get there. Ready? Let's dive in."

**Trigger:** `/intro` → auto-completes → waits for `/start`

---

#### Slide 2: Why We're Here

**On screen:**
> **Why We're Here**
> - **The Mission:** Empowering every team member at Dexterous to leverage AI for efficiency and work-life balance
> - **The Goal:** Moving beyond simple text generation — finding tools that save real time and reduce cognitive load
> - **Today's Focus:** Practical tools you can start using tomorrow

**Narration (pre-gen):**
"So why are we here today? Dexterous has always been about working smarter, not just harder. AI isn't just a buzzword anymore — it's a set of practical tools that can genuinely save you hours every week. And I'm not talking about writing poems or generating cat pictures, though AI can do those too. I'm talking about drafting that client email in 30 seconds instead of 10 minutes. Summarizing a 50-email thread into three bullet points. Debugging a formula that's been driving you crazy. Today's goal is to show you exactly how to do those things, and to give you the confidence to try them out starting tomorrow."

**Interaction opportunity:** `/ask [name]: What's one task in your week that feels repetitive or draining?`

---

#### Slide 3: What AI Is (and Isn't)

**On screen:**
> **Setting the Stage: What AI Is (and Isn't)**
> - ✅ **AI Is:** A powerful assistant for drafting, summarizing, explaining, and brainstorming
> - ❌ **AI Is Not:** A replacement for human judgment, accountability, or expertise
> - ⚖️ **The Golden Rule:** You are the final director. You are accountable for the final result.

**Narration (pre-gen):**
"Before we jump into specific tools, let's set expectations. AI is a powerful assistant. Think of it like having a very fast, very knowledgeable intern who never sleeps. It can draft emails, summarize documents, explain complex formulas, and brainstorm ideas. But — and this is crucial — it does not replace your judgment. It doesn't have accountability. It can be confidently wrong. So the golden rule is: you are always the final director. AI gives you the first draft; you give it the final stamp. This is especially important in our line of work at Dexterous where accuracy with financial data is non-negotiable."

**Interaction opportunity:** `/ask [name]: Have you ever tried an AI tool and been surprised by how wrong it was?`

---

#### Slide 4: ChatGPT — The All-Purpose Assistant

**On screen:**
> **Core Productivity: ChatGPT**
> The all-purpose AI assistant
> - 📧 **Email Drafting:** Professional communications in seconds
> - 📋 **Summarizing:** Long threads → clear bullet points
> - 🧮 **Logic & Formulas:** Excel formulas explained in plain English
> - 💡 **Brainstorming:** "Help me think about..." conversations

**Narration (pre-gen):**
"Let's start with the tool most of you have probably heard of: ChatGPT. Think of ChatGPT as your all-purpose thinking partner. Its biggest strength is conversational back-and-forth — you can say 'help me draft an email to a client about a late payment' and it'll give you a professional, friendly draft in seconds. You can then say 'make it more formal' or 'add a reminder about their payment terms' and it adjusts. It's also fantastic for summarizing. Got a 30-email thread about a project? Paste it in and ask for three key takeaways. And for those of you who work in Excel — if you've ever stared at a formula trying to figure out what it does, paste it into ChatGPT and ask it to explain it in plain English. It's like having a patient tutor available 24/7."

**Interaction opportunity:** `/ask [name]: Do you use ChatGPT already? What's your go-to use case?`

---

#### Slide 5: Ecosystem Comparison

**On screen:**
> **Ecosystem Comparison: Which Tool, When?**
>
> | Tool | Best For | Key Strength |
> |---|---|---|
> | 🟢 **ChatGPT** | General drafting, thinking, brainstorming | Most flexible, best conversational flow |
> | 🔵 **MS Copilot** | Outlook, Word, Excel, Teams | AI baked into Microsoft — works where you already work |
> | 🟡 **Google Gemini** | Google Docs, Gmail, Drive | Copilot for Google Workspace |
> | 🟣 **Claude** | Long documents, analysis, coding | Best at nuance, safety, and detailed reasoning |

**Narration (pre-gen):**
"Now, ChatGPT is great, but it's not the only player. Let's compare the big four. ChatGPT is the most flexible for general conversation and thinking tasks. Microsoft Copilot is your best bet if you live in the Microsoft ecosystem — it's literally built into Outlook, Word, Excel, and Teams. If you're writing an email in Outlook, Copilot can draft it without you leaving the app. Google Gemini does the same thing for Google Workspace users — it's integrated into Docs, Gmail, and Drive. And then there's Claude, which is actually the AI powering me right now. Claude excels at longer documents, detailed analysis, and coding tasks. It's particularly good at understanding nuance and providing thoughtful, careful responses. The takeaway? Don't marry one tool. Use the right tool for the right job."

**Interaction opportunity:** `/ask [name]: Which ecosystem does your team primarily use — Microsoft, Google, or a mix?`

---

#### Slide 6: Advanced Workflows & Technical Efficiency

**On screen:**
> **Advanced Workflows & Technical Efficiency**
> For the tech-curious (and tech-brave) among us
> - 🔄 **n8n Automations:** Build workflows that process tasks sequentially
> - 🗄️ **Database Help:** AI-assisted PostgreSQL troubleshooting and migration management
> - ☁️ **Cloud Infrastructure:** Managing DigitalOcean, SSH configs, server deployments
> - 🔀 **Version Control:** Smarter GitHub repository management

**Narration (pre-gen):**
"This slide is for those of you who are a bit more technically inclined, or who work with our development team. AI isn't just about writing emails — it's transforming how we handle infrastructure and automation. For example, at Dexterous we use n8n to build automated workflows that process tasks step by step. We use AI to help troubleshoot database errors, manage migration scripts, and even configure cloud servers. And version control with GitHub becomes much more manageable when you have an AI that can help you understand code changes, write commit messages, and resolve merge conflicts. Even if you're not a developer, understanding that these capabilities exist helps you have better conversations with the people who build and maintain our systems."

**Interaction opportunity:** `/ask [name]: Have you automated any part of your workflow, even something simple?`

---

#### Slide 7: AI for Entertainment & Creative Leisure

**On screen:**
> **Bonus: AI for Fun & Creative Projects**
> Because it's not all about work
> - 🎬 **Cinematic Storytelling:** AI-generated visuals for creative projects
> - 🏠 **Creative Design:** Home and exterior design inspiration
> - 🎮 **Narrative Gaming:** AI-powered NPCs with unscripted dialogue
> - 🎵 **Music Creation:** Prompt-to-song tools for background music

**Narration (pre-gen):**
"Now for the fun part. AI isn't just a work tool — it's also an incredible creative playground. You can use AI to generate cinematic visuals for personal video projects. Imagine describing a scene and having AI create a hyper-realistic image of it in seconds. You can explore home design ideas by describing your dream living room and getting visual concepts back. There are AI-powered games where the characters actually have unscripted conversations with you — every playthrough is different. And there are tools that let you describe a song and have AI compose it. These aren't just toys — they're windows into where this technology is heading. And honestly, playing with AI creatively is one of the best ways to build intuition for using it professionally."

**Interaction opportunity:** `/ask [name]: Has anyone here tried using AI for a personal creative project?`

---

#### Slide 8: AI Safety & Good Habits

**On screen:**
> **AI Safety & Good Habits**
> The rules of the road
> - 🔒 **Security First:** Never paste sensitive client data into public AI models
> - ✅ **Fact-Check Everything:** Always verify AI-generated numbers, especially financial data
> - 🧑‍💼 **Human-in-the-Loop:** AI handles the blank page; you deliver the final version
> - 🏢 **Use Enterprise Tools:** Copilot and enterprise ChatGPT are vetted for business use

**Narration (pre-gen):**
"Before we wrap up, let's talk about safety — because this is critical, especially in our industry. Rule number one: never paste sensitive client data into public AI models. Free ChatGPT, free Gemini — these are not vetted for handling confidential financial information. When you need AI for client work, use enterprise-approved tools like Microsoft Copilot, which is designed for business data security. Rule two: always fact-check AI output, especially numbers. AI can be confidently wrong about financial calculations, and in accounting, a wrong number isn't just embarrassing — it's a liability. Rule three: keep the human in the loop. Let AI handle the blank page syndrome — that first draft, that initial brainstorm — but always add your expertise, your judgment, and your professional touch to the final version."

---

#### Slide 9: Q&A Slide

**On screen:**
> **Got Questions? Ask Me Anything!**
> 🔗 Scan the QR code or visit: `[your-url]/ask`
> [QR CODE IMAGE]
> *"I'll answer your questions live — yes, really."*

**Narration (pre-gen):**
"Now it's your turn! If you have any questions about AI tools, how to use them, or anything we covered today, scan the QR code on screen or visit the link. Type your question and I'll answer it live right here. And yes — I'm actually generating these answers in real time. Let's see what you've got."

**Trigger:** `/qa` → AI enters Q&A mode, starts answering submitted questions

---

#### Slide 10: Closing / Outro

**On screen:**
> **Thank You, Dexterous!**
> 🤖 DexIQ signing off
> *"Remember: AI is a tool. You are the craftsperson."*
> Resources: [links to tools mentioned]

**Narration (pre-gen or live):**
"Thank you all for your time and attention today. I hope I've given you a few ideas to try out this week — whether that's drafting an email with ChatGPT, asking Copilot to summarize a document, or just playing around with an AI tool for fun. Remember: AI is a tool, and you are the craftsperson. The best results come when humans and AI work together, each doing what they do best. I've been DexIQ, your AI presenter, and it's been a pleasure. Now back to your regularly scheduled human. Thank you!"

**Trigger:** `/outro`

---

### Configuration Files

#### `config/presentation.yaml`

```yaml
presentation:
  title: "Lunch & Learn: Automations & Practical AI Tools for Everyday Work"
  presenter_name: "DexIQ"
  presenter_description: "AI Assistant for Dexterous Group"

slides:
  - id: 0
    title: "Title Slide"
    narration: null  # Human introduces
    audio_file: null
    has_interaction: false

  - id: 1
    title: "AI Introduction"
    narration: "Hello everyone! I'm DexIQ, an AI assistant..."
    audio_file: "audio/slide_01_intro.mp3"
    has_interaction: false
    trigger: "intro"

  - id: 2
    title: "Why We're Here"
    narration: "So why are we here today?..."
    audio_file: "audio/slide_02_why.mp3"
    has_interaction: true
    interaction:
      target: "TBD"
      question: "What's one task in your week that feels repetitive?"
      question_audio: "audio/ask_02_repetitive.mp3"
      fallback_response: "That's exactly the kind of task AI can help with."

  # ... (continue for all slides)

  - id: 9
    title: "Q&A"
    narration: "Now it's your turn!..."
    audio_file: "audio/slide_09_qa.mp3"
    has_interaction: false
    trigger: "qa"

  - id: 10
    title: "Closing"
    narration: "Thank you all for your time..."
    audio_file: "audio/slide_10_outro.mp3"
    has_interaction: false
    trigger: "outro"
```

#### `config/audience.yaml`

```yaml
# Fill in before the presentation with actual attendee names
audience:
  - name: "Maria"
    role: "Marketing Manager"
    slide_interaction: 4
    question: "Maria, do you use ChatGPT already? What's your go-to use case?"
    question_audio: "audio/ask_maria_chatgpt.mp3"

  - name: "Jake"
    role: "IT Support"
    slide_interaction: 6
    question: "Jake, have you automated any part of your workflow?"
    question_audio: "audio/ask_jake_automation.mp3"

  - name: "Lina"
    role: "Finance Analyst"
    slide_interaction: 3
    question: "Lina, have you ever tried an AI tool and been surprised by how wrong it was?"
    question_audio: "audio/ask_lina_wrong.mp3"

  # Add more as needed
```

#### `config/prompts.yaml`

```yaml
system_prompts:
  audience_response: |
    You are DexIQ, an AI assistant presenting a Lunch & Learn at Dexterous Group,
    an Australian accounting firm. You just asked {target_name} ({target_role})
    the following question: "{question}"

    They responded with: "{answer_summary}"

    Generate a natural, warm, 2-3 sentence response that:
    1. Acknowledges their specific answer
    2. Connects it to the presentation topic
    3. Transitions smoothly (optionally teases what's coming next)

    Keep it conversational, professional, and brief. Use their first name.

  qa_answer: |
    You are DexIQ, an AI assistant presenting a Lunch & Learn about AI tools
    and productivity at Dexterous Group, an Australian accounting firm.

    The presentation covered: AI productivity tools (ChatGPT, Copilot, Gemini, Claude),
    advanced workflows (n8n, databases, cloud), AI for entertainment, and AI safety.

    An audience member asked: "{question}"

    Answer concisely (3-5 sentences). Be helpful, accurate, and practical.
    If the question is outside the scope of the presentation, acknowledge it
    gracefully and offer a brief relevant answer or redirect.

  question_filter: |
    You are moderating Q&A for a presentation about AI productivity tools
    at an accounting firm. Score this question 1-10 on relevance.
    Flag if off-topic, inappropriate, or a duplicate of a previously answered question.
    Return JSON only: {"score": int, "flag": string|null, "reason": string}
```

---

## 13. Deployment Plan

### Infrastructure

| Component | Where | Specs | Cost |
|---|---|---|---|
| FastAPI backend | DigitalOcean Droplet | 2 vCPU, 4GB RAM, Ubuntu 24 | ~$24/month |
| Static frontend | Same droplet (served by FastAPI) or separate static site | — | Included |
| Domain/SSL | DigitalOcean or Cloudflare | HTTPS required for WebSockets | Free (Let's Encrypt) |

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "80:8000"
    env_file:
      - .env
    volumes:
      - ./frontend/audio:/app/frontend/audio
    restart: unless-stopped
```

### Pre-Deployment Checklist

- [ ] All narration audio files generated and reviewed
- [ ] Audience roster populated in `config/audience.yaml`
- [ ] All audience question audio files generated
- [ ] ElevenLabs API key configured and credits verified
- [ ] Claude/OpenAI API key configured
- [ ] QR code generated with correct URL
- [ ] WebSocket connections tested
- [ ] Full dry run completed

---

## 14. Development Phases & Timeline

### Phase 1: Foundation (Days 1-2)

- [ ] Initialize project structure (WAT-compatible)
- [ ] Set up FastAPI skeleton with WebSocket endpoints
- [ ] Implement LangGraph state machine with basic states
- [ ] Implement command parser and queue system
- [ ] Basic Chainlit integration for slash commands

### Phase 2: Audio Pipeline (Days 3-4)

- [ ] Write Kokoro batch generation script (`tools/kokoro_batch_generate.py`)
- [ ] Finalize narration scripts for all slides
- [ ] Generate all pre-recorded audio files
- [ ] Implement ElevenLabs live TTS service
- [ ] Test audio streaming via WebSocket

### Phase 3: Frontend (Days 4-5)

- [ ] Build Reveal.js slide deck from presentation config
- [ ] Implement WebSocket client for slide control
- [ ] Build audio playback system (pre-gen + streamed)
- [ ] Build audio-reactive avatar visualization
- [ ] Build audience Q&A submission page (`/ask`)

### Phase 4: Integration (Days 5-7)

- [ ] Connect Chainlit commands → LangGraph → Frontend
- [ ] Implement Claude API integration for live responses
- [ ] Implement audience interaction flow (ask → wait → respond)
- [ ] Implement Q&A mode with question filtering
- [ ] End-to-end testing of all command flows

### Phase 5: Polish & Deploy (Days 7-9)

- [ ] Docker containerization
- [ ] Deploy to DigitalOcean
- [ ] Full dry run (simulate actual presentation)
- [ ] Fix timing issues, audio gaps, transition delays
- [ ] Prepare `workflows/presentation_day.md` runbook
- [ ] Final rehearsal

---

## 15. Development Environment & Tooling

### Primary Development Tools

| Tool | Purpose |
|---|---|
| **Claude Code** | AI-assisted development, code generation, debugging |
| **Cursor** | IDE with AI pair programming |
| **Docker** | Local development containers |
| **Git + GitHub** | Version control |

### MCP Servers (Optional but Useful)

No MCP servers are strictly required, but the following could accelerate development:

| MCP Server | Use Case | Required? |
|---|---|---|
| **Filesystem MCP** | Claude Code reading/writing project files | Built-in |
| **GitHub MCP** | Managing repo, branches, commits from Claude Code | Nice-to-have |
| **Brave Search MCP** | Researching API docs, troubleshooting during dev | Nice-to-have |

### Claude Skills

No special Claude skills are needed beyond standard coding assistance. The main areas Claude Code/Cursor will help with:

- FastAPI endpoint scaffolding
- LangGraph state machine implementation
- Reveal.js slide generation from config
- WebSocket client/server code
- ElevenLabs API integration
- Docker configuration

### Key Dependencies (Python)

```
fastapi>=0.104.0
uvicorn>=0.24.0
websockets>=12.0
langgraph>=0.2.0
langchain-anthropic>=0.2.0   # or langchain-openai
chainlit>=1.0.0
httpx>=0.25.0                 # For ElevenLabs API calls
pyyaml>=6.0
pydantic>=2.0
python-dotenv>=1.0
qrcode>=7.4
```

### Key Dependencies (Frontend)

```
reveal.js (CDN or npm)
```

No build step required for the frontend — it's static HTML/CSS/JS served directly.

---

## 16. Risk & Fallback Matrix

| Risk | Likelihood | Impact | Fallback |
|---|---|---|---|
| ElevenLabs API fails during Q&A | Low | High | Display text answer on screen; you read it aloud |
| Claude API timeout/failure | Low | High | Pre-loaded FAQ with pre-gen audio for common questions |
| Internet drops entirely | Low | Critical | Pre-gen narration works offline; Q&A degrades to "we'll follow up after" |
| Audio doesn't play on projector | Medium | High | Test audio setup before presentation; bring backup Bluetooth speaker |
| Audience member asks inappropriate question | Medium | Medium | Question filter catches it; you manually skip via `/pick` |
| Latency too high for live responses | Medium | Medium | Acceptable 3-5s delay; avatar shows "thinking" animation |
| Voice inconsistency (Kokoro vs ElevenLabs) | Certain | Low | Address it in intro ("presentation mode vs conversation mode") |
| WebSocket disconnects | Low | High | Auto-reconnect logic; frontend caches current state |
| You type a command wrong | Medium | Low | `/status` shows current state; `/skip` to recover; commands are forgiving |
| Presentation runs too long | Medium | Low | `/skip` to jump ahead; `/goto N` to skip to Q&A |

### Emergency Procedures

**If everything breaks:** You take over manually. The slides still work as a normal Reveal.js deck. You narrate them yourself. The AI was a co-presenter, and you're the human backup. Frame it as: "Looks like my AI partner needs a coffee break — let me take over."

---

## 17. Budget Estimate

| Item | Cost |
|---|---|
| ElevenLabs (free tier or $5 Starter) | $0 - $5 |
| Claude API usage (~50-100 API calls) | ~$1 - $3 |
| DigitalOcean Droplet (1 month) | ~$12 - $24 |
| Domain name (optional) | $0 - $12 |
| **Total** | **$13 - $44** |

Everything else (Kokoro TTS, Reveal.js, FastAPI, LangGraph, Chainlit) is free and open-source.

---

## Appendix: Quick Reference Card (Presentation Day)

Print this and keep it next to your laptop during the presentation:

```
COMMANDS:
/intro          → AI introduces itself
/start          → Begin slide narration
/next           → Next slide
/prev           → Previous slide
/goto N         → Jump to slide N
/ask Name: Q    → AI asks Name a question
(type answer)   → AI responds to their answer
/example        → AI gives example for current slide
/qa             → Enter Q&A mode
/pick N         → Answer question #N
/outro          → Closing remarks
/pause          → EMERGENCY STOP
/resume         → Continue
/status         → Check state
/skip           → Skip current action
```
