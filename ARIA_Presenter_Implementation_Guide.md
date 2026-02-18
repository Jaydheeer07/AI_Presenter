# ARIA AI Presenter — Master Implementation Guide
## Complete Slide Overhaul: All 14 Slides (v1 + v2 Combined)

> **For AI Coding IDEs (Cursor / Windsurf / Claude Code)**
>
> This document is the single source of truth for all presentation changes.
> It covers every slide's updated HTML content, narration scripts, backend
> changes, and new features. Implement changes in the order they appear.
> Do not proceed without reading the full relevant section first.

---

## Table of Contents

1. [Project Overview & Constraints](#1-project-overview--constraints)
2. [New Slide Architecture (14 slides)](#2-new-slide-architecture-14-slides)
3. [Files to Change — Summary Table](#3-files-to-change--summary-table)
4. [Phase 1 — Presenter Rename (DexIQ → ARIA)](#4-phase-1--presenter-rename-dexiq--aria)
5. [Phase 2 — Frontend Slide HTML Changes](#5-phase-2--frontend-slide-html-changes)
6. [Phase 3 — CSS Additions](#6-phase-3--css-additions)
7. [Phase 4 — Narration Scripts (presentation.yaml)](#7-phase-4--narration-scripts-presentationyaml)
8. [Phase 5 — Backend Changes (actions.py, states.py)](#8-phase-5--backend-changes-actionspy-statespy)
9. [Phase 6 — Supabase Q&A Integration](#9-phase-6--supabase-qa-integration)
10. [Phase 7 — Media Assets & Audio Migration](#10-phase-7--media-assets--audio-migration)
11. [Phase 8 — Audio Generation Checklist](#11-phase-8--audio-generation-checklist)
12. [Verification Checklist](#12-verification-checklist)

---

## 1. Project Overview & Constraints

### Stack
- **Frontend:** Reveal.js 5.1.0 (via CDN), custom HTML/CSS, vanilla JS WebSocket client
- **Backend:** FastAPI + LangGraph state machine, Python
- **TTS:** Kokoro (local Docker), pre-generated MP3 files
- **Audio path:** `frontend/audio/*.mp3`
- **Video path:** `frontend/video/*.mp4` *(new directory — create it)*
- **Fonts:** Plus Jakarta Sans (display), Space Mono (mono) via Google Fonts

### Critical Constraints
- Reveal.js `fragments: false` — all content appears immediately on slide entry (no click-to-reveal)
- Reveal.js `keyboard: false` and `touch: false` — slides controlled exclusively by WebSocket backend commands
- `center: false` in Reveal config — vertical centering is handled by CSS flexbox
- Do NOT add `position: relative` to `<section>` elements — Reveal.js needs `position: absolute`
- Slide sections use `data-slide-id` attribute for identification
- All CSS changes go into `frontend/css/theme.css` — do NOT create new CSS files

### Presenter Identity
- **Old name:** DexIQ
- **New name:** ARIA (Automated Reasoning & Intelligent Assistant)
- **Gender:** Female voice
- **Built by:** Dexterous Group

---

## 2. New Slide Architecture (14 Slides)

| Slide # | `data-slide-id` | Title | Status |
|---------|-----------------|-------|--------|
| 0 | 0 | Title / Welcome | Update name only |
| 1 | 1 | Meet ARIA (Intro) | Update name + content |
| 2 | 2 | Why Should You Care About AI? | Full rewrite |
| 3 | 3 | What AI Is & Isn't | Minor improvements |
| 4 | 4 | ChatGPT Capabilities | Full rewrite |
| 5 | 5 | The AI Ecosystem | Full rewrite + reorder |
| 6 | 6 | Prompt Engineering 101 | No HTML change |
| 7 | 7 | Prompting Like a Pro | Full rewrite (was Advanced Use Cases) |
| 8 | 8 | Advanced AI Tools | Full rewrite (was Entertainment) |
| 9 | 9 | AI Images & Video | NEW slide |
| 10 | 10 | AI Music & Creative Writing | NEW slide |
| 11 | 11 | AI Safety & Best Practices | Minor fix (was slide 9) |
| 12 | 12 | Q&A — Ask ARIA | Update QR + wording |
| 13 | 13 | The Meta Moment | Move here (was slide 10) |
| 14 | 14 | Outro — I've been ARIA | New narration (was slide 12) |

**Total: 15 slides** (indices 0–14)

> **Note on current audio files:** The existing `slide_07_advanced.mp3` through `slide_12_outro.mp3`
> will all need to be re-recorded because their content is changing. See Phase 7 & 8.

---

## 3. Files to Change — Summary Table

| File | Action | Reason |
|------|--------|--------|
| `frontend/index.html` | **REPLACE** | 15 slides, new content, new slides 9 & 10 |
| `frontend/css/theme.css` | **ADD** new classes | Carousel, video tiles, music player, new grid layouts |
| `config/presentation.yaml` | **REPLACE** | Updated narrations, 15 slides, ARIA name |
| `backend/agent/actions.py` | **MODIFY** | Update `SLIDE_AUDIO_MAP` (indices → 14), update `qa_mode_node` and `outro_node` slide indices |
| `backend/agent/states.py` | **MODIFY** | Change `total_slides` default from `13` → `15` |
| `frontend/ask.html` | **MODIFY** | Update title/branding from DexIQ → ARIA, add Supabase POST |
| `backend/services/question_manager.py` | **MODIFY** | Add Supabase persistence alongside existing in-memory store |
| `backend/routers/audience.py` | **MODIFY** | POST `/audience/question` writes to Supabase |
| `frontend/video/` | **CREATE** directory | Store Seedance MP4 clips |
| `frontend/audio/ai_music_sample.mp3` | **ADD** | Your downloaded AI music clip |

---

## 4. Phase 1 — Presenter Rename (DexIQ → ARIA)

Do a **global find-and-replace** across the entire project before any other changes:

### String Replacements (exact, case-sensitive)

| Find | Replace | Files |
|------|---------|-------|
| `DexIQ AI Presenter` | `ARIA AI Presenter` | `index.html`, `ask.html`, `presentation.yaml`, any Python log strings |
| `Hi, I'm DexIQ` | `Hi, I'm ARIA` | `index.html` |
| `I've been DexIQ` | `I've been ARIA` | `presentation.yaml` (outro narration) |
| `presenter_name: "DexIQ"` | `presenter_name: "ARIA"` | `presentation.yaml` |
| `Ask a Question — DexIQ` | `Ask a Question — ARIA` | `ask.html` `<title>` |
| `DexIQ is introducing` | `ARIA is introducing` | `actions.py` log strings |
| `DexIQ is delivering` | `ARIA is delivering` | `actions.py` log strings |

### In `presentation.yaml` header section:
```yaml
presentation:
  title: "Lunch & Learn: Automations & Practical AI Tools for Everyday Work"
  presenter_name: "ARIA"
  presenter_description: "Automated Reasoning & Intelligent Assistant — Built by Dexterous Group"
  total_slides: 15
```

---

## 5. Phase 2 — Frontend Slide HTML Changes

Replace the entire `<div class="slides">` block in `frontend/index.html`.
The complete new slide markup follows. Preserve all non-slide HTML above and below
(the avatar overlay, question overlay, response overlay, start overlay, audio element,
script tags, and Reveal.js init block).

---

### SLIDE 0 — Title

No structural change. Update text only:

```html
<!-- ══════════ SLIDE 0 — Title ══════════ -->
<section data-slide-id="0">
  <div class="gradient-mesh"></div>
  <div class="bg-arcs">
    <div class="arc"></div><div class="arc"></div><div class="arc"></div><div class="arc"></div>
  </div>
  <div class="slide-content title-slide">
    <div class="title-badge">Live AI Presentation</div>
    <h1 class="title-main">
      Welcome to<br>
      <span class="highlight-teal">ARIA</span> <span class="highlight-gold">AI Presenter</span>
    </h1>
    <p class="title-sub">
      An AI-powered presentation system built by Dexterous Group — where accounting intelligence meets cutting-edge technology.
    </p>
    <div class="stats-row">
      <div class="stat-item">
        <div class="stat-value">15</div>
        <div class="stat-label">Live Slides</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">AI</div>
        <div class="stat-label">Narrated</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">&infin;</div>
        <div class="stat-label">Q&amp;A Ready</div>
      </div>
    </div>
  </div>
  <div class="watermark-arcs"><div class="warc"></div><div class="warc"></div><div class="warc"></div></div>
</section>
```

---

### SLIDE 1 — Meet ARIA

```html
<!-- ══════════ SLIDE 1 — Intro ══════════ -->
<section data-slide-id="1">
  <div class="gradient-mesh"></div>
  <div class="slide-content intro-slide">
    <div class="badge">Meet Your AI Host</div>
    <h2 class="slide-title">Hi, I'm <span class="highlight-teal">ARIA</span></h2>
    <p class="slide-subtitle">
      Automated Reasoning &amp; Intelligent Assistant — built by Dexterous Group.<br>
      Not a human. Not a recording. Everything you hear is generated live, just for this room.
    </p>
    <div class="intro-features">
      <span class="feature-chip">&#x1F9E0; Powered by Claude AI</span>
      <span class="feature-chip">&#x1F399;&#xFE0F; Live Voice Synthesis</span>
      <span class="feature-chip">&#x1F4AC; Real-Time Q&amp;A</span>
      <span class="feature-chip">&#x26A1; Responds in Seconds</span>
    </div>
    <blockquote class="intro-quote">
      "Think of me as your smartest colleague — one who's read everything, never gets tired,
      and always has an answer. Though I'm still working on my coffee order."
    </blockquote>
  </div>
  <div class="watermark-arcs"><div class="warc"></div><div class="warc"></div><div class="warc"></div></div>
</section>
```

---

### SLIDE 2 — Why Should You Care About AI?

Full rewrite — concrete accounting examples instead of abstract pillars.

```html
<!-- ══════════ SLIDE 2 — Why Should You Care? ══════════ -->
<section data-slide-id="2">
  <div class="gradient-mesh"></div>
  <div class="slide-content">
    <div class="badge">What's In It For You?</div>
    <h2 class="slide-title">Why AI Matters for <span class="highlight-gold">YOUR Work</span></h2>
    <p class="slide-subtitle">These aren't future possibilities — you can do all of this today.</p>
    <div class="three-cards">
      <div class="info-card">
        <div class="card-icon">&#x2709;&#xFE0F;</div>
        <div class="card-label">Email Drafts</div>
        <div class="card-text">
          <em>"Write a follow-up email to a client whose invoice is 14 days late."</em><br>
          &rarr; Professional draft in under 30 seconds.
        </div>
      </div>
      <div class="info-card">
        <div class="card-icon">&#x1F4C4;</div>
        <div class="card-label">Document Summaries</div>
        <div class="card-text">
          <em>"Summarise this 40-page engagement letter into 5 key points."</em><br>
          &rarr; Done before you finish your coffee.
        </div>
      </div>
      <div class="info-card">
        <div class="card-icon">&#x1F4CA;</div>
        <div class="card-label">Excel Help</div>
        <div class="card-text">
          <em>"Explain what this formula does in plain English."</em><br>
          &rarr; Instant, patient, always available.
        </div>
      </div>
    </div>
  </div>
</section>
```

---

### SLIDE 3 — What AI Is & Isn't

Minor content improvements — accounting-specific language.

```html
<!-- ══════════ SLIDE 3 — What AI Is / Isn't ══════════ -->
<section data-slide-id="3">
  <div class="gradient-mesh"></div>
  <div class="slide-content">
    <div class="badge">Setting Expectations</div>
    <h2 class="slide-title">What AI <span class="highlight-teal">Is</span> &amp; <span class="highlight-gold">Isn't</span></h2>
    <div class="two-columns">
      <div class="column">
        <div class="column-header teal">&#x2713; AI Is</div>
        <div class="clean-list">
          <div class="list-item">A tireless drafter — emails, reports, summaries</div>
          <div class="list-item">A 24/7 tutor for formulas and concepts</div>
          <div class="list-item">A pattern-spotter in data and documents</div>
          <div class="list-item">Getting significantly better every 6 months</div>
        </div>
      </div>
      <div class="column">
        <div class="column-header gold">&#x2717; AI Isn't</div>
        <div class="clean-list">
          <div class="list-item">Infallible — it can "hallucinate" convincingly</div>
          <div class="list-item">Accountable — you own the final output</div>
          <div class="list-item">A replacement for professional judgment</div>
          <div class="list-item">Safe with sensitive client data on free plans</div>
        </div>
      </div>
    </div>
    <div class="golden-rule">
      <strong>Golden Rule:</strong> AI gives you the first draft. You give it the final stamp.
      In accounting, that distinction matters.
    </div>
  </div>
</section>
```

---

### SLIDE 4 — ChatGPT Capabilities

Full rewrite — practical capabilities for accountants, not LLM mechanics.

```html
<!-- ══════════ SLIDE 4 — ChatGPT Capabilities ══════════ -->
<section data-slide-id="4">
  <div class="gradient-mesh"></div>
  <div class="slide-content">
    <div class="badge">Your AI Thinking Partner</div>
    <h2 class="slide-title">ChatGPT: What Can It <span class="highlight-teal">Actually Do?</span></h2>
    <p class="slide-subtitle">The most versatile AI tool — and how accountants use it every day.</p>
    <div class="icon-grid">
      <div class="icon-item">
        <div class="icon-circle">&#x2709;&#xFE0F;</div>
        <div>
          <div class="icon-label">Draft &amp; Rewrite</div>
          <div class="icon-desc">"Write a professional email declining a fee reduction request while keeping the relationship warm."</div>
        </div>
      </div>
      <div class="icon-item">
        <div class="icon-circle">&#x1F4CB;</div>
        <div>
          <div class="icon-label">Summarise &amp; Extract</div>
          <div class="icon-desc">"Summarise this email thread and list the 3 key decisions that were made."</div>
        </div>
      </div>
      <div class="icon-item">
        <div class="icon-circle">&#x1F4D0;</div>
        <div>
          <div class="icon-label">Explain &amp; Teach</div>
          <div class="icon-desc">"Explain what this Excel VLOOKUP formula does in plain English."</div>
        </div>
      </div>
      <div class="icon-item">
        <div class="icon-circle">&#x1F504;</div>
        <div>
          <div class="icon-label">Iterate &amp; Refine</div>
          <div class="icon-desc">Keep the conversation going — "make it more formal" or "add a deadline reminder" — and it adjusts.</div>
        </div>
      </div>
    </div>
    <div class="golden-rule">
      &#x1F4A1; Pro tip: ChatGPT remembers the context of your conversation — keep refining until you get exactly what you need.
    </div>
  </div>
</section>
```

---

### SLIDE 5 — The AI Ecosystem

Full rewrite — reordered to match narration (ChatGPT → Copilot → Gemini → Claude) with expanded specialist tools section.

```html
<!-- ══════════ SLIDE 5 — AI Ecosystem ══════════ -->
<section data-slide-id="5">
  <div class="gradient-mesh"></div>
  <div class="slide-content">
    <div class="badge">The Landscape</div>
    <h2 class="slide-title">The AI <span class="highlight-gold">Ecosystem</span></h2>
    <p class="slide-subtitle">The Big Four — and a few specialists worth knowing.</p>
    <div class="tool-cards">
      <div class="tool-card">
        <div class="tool-color" style="background: #10A37F;"></div>
        <div class="card-icon">&#x1F49A;</div>
        <div class="card-label">ChatGPT</div>
        <div class="card-text">OpenAI's flagship. Best all-rounder for writing, analysis, and brainstorming.</div>
        <div class="tool-tip">Best for: General tasks</div>
      </div>
      <div class="tool-card">
        <div class="tool-color" style="background: #0467DF;"></div>
        <div class="card-icon">&#x1F916;</div>
        <div class="card-label">Copilot</div>
        <div class="card-text">Microsoft's AI. Built directly into Outlook, Word, Excel, and Teams.</div>
        <div class="tool-tip">Best for: Office workflows</div>
      </div>
      <div class="tool-card">
        <div class="tool-color" style="background: #4285F4;"></div>
        <div class="card-icon">&#x1F537;</div>
        <div class="card-label">Gemini</div>
        <div class="card-text">Google's model. Integrated into Gmail, Docs, and Drive. Strong at research.</div>
        <div class="tool-tip">Best for: Google Workspace</div>
      </div>
      <div class="tool-card">
        <div class="tool-color" style="background: var(--dex-teal);"></div>
        <div class="card-icon">&#x1F9E0;</div>
        <div class="card-label">Claude</div>
        <div class="card-text">Anthropic's model — powers me. Excels at long documents and nuanced analysis.</div>
        <div class="tool-tip">Best for: Deep analysis</div>
      </div>
    </div>
    <div class="specialist-bar">
      <span class="specialist-label">&#x1F50D; Specialists:</span>
      <span class="specialist-chip">Perplexity — research with citations</span>
      <span class="specialist-chip">Otter.ai — meeting transcription</span>
      <span class="specialist-chip">DeepSeek — free powerful reasoning</span>
      <span class="specialist-chip">Grok — real-time web access</span>
    </div>
  </div>
</section>
```

---

### SLIDE 6 — Prompt Engineering 101

**No HTML changes needed.** Narration update only (see Phase 4).

---

### SLIDE 7 — Prompting Like a Pro

Full rewrite — replaces old "Advanced Use Cases" content with advanced prompting techniques.

```html
<!-- ══════════ SLIDE 7 — Prompting Like a Pro ══════════ -->
<section data-slide-id="7">
  <div class="gradient-mesh"></div>
  <div class="slide-content">
    <div class="badge">Level Up</div>
    <h2 class="slide-title">Prompting <span class="highlight-teal">Like a Pro</span></h2>
    <p class="slide-subtitle">Six techniques that separate good AI output from brilliant AI output.</p>
    <div class="prompt-tips pro-tips-grid">
      <div class="tip-item">
        <div class="tip-num">5</div>
        <div class="tip-text"><strong>Specify your format</strong> — "Give me a numbered list, under 200 words, with a one-line summary at the top."</div>
      </div>
      <div class="tip-item">
        <div class="tip-num">6</div>
        <div class="tip-text"><strong>Set constraints</strong> — "Australian English. No legal jargon. Under 200 words."</div>
      </div>
      <div class="tip-item">
        <div class="tip-num">7</div>
        <div class="tip-text"><strong>Think step by step</strong> — Add "reason through this before answering" for anything involving logic or numbers.</div>
      </div>
      <div class="tip-item">
        <div class="tip-num">8</div>
        <div class="tip-text"><strong>Give context first</strong> — Paste the email thread, document, or background before asking your question.</div>
      </div>
      <div class="tip-item">
        <div class="tip-num">9</div>
        <div class="tip-text"><strong>Ask for alternatives</strong> — "Give me 3 versions: one formal, one casual, one brief."</div>
      </div>
      <div class="tip-item">
        <div class="tip-num">10</div>
        <div class="tip-text"><strong>Stack role + audience</strong> — "Act as a senior tax advisor explaining this to a client with no finance background."</div>
      </div>
    </div>
    <div class="golden-rule">
      &#x1F3AF; <strong>Pro move:</strong> Chain them all — role + context + constraints + format + audience = output you can send as-is.
    </div>
  </div>
</section>
```

---

### SLIDE 8 — Advanced AI Tools

Full rewrite — automation platforms + AI coding tools, using tool-cards layout.

```html
<!-- ══════════ SLIDE 8 — Advanced AI Tools ══════════ -->
<section data-slide-id="8">
  <div class="gradient-mesh"></div>
  <div class="slide-content">
    <div class="badge">Power Tools</div>
    <h2 class="slide-title">AI for the <span class="highlight-gold">Builders &amp; Automators</span></h2>
    <p class="slide-subtitle">Beyond chatbots — tools that transform how work gets done at scale.</p>

    <div class="tools-section-label">&#x2699;&#xFE0F; Automation Platforms</div>
    <div class="tool-cards">
      <div class="tool-card">
        <div class="tool-color" style="background: #EA4B71;"></div>
        <div class="card-icon">&#x1F504;</div>
        <div class="card-label">n8n</div>
        <div class="card-text">Open-source, self-hosted. AI-native with LangChain integration for complex multi-step agent workflows.</div>
        <div class="tool-tip">Best for: Dev &amp; tech teams</div>
      </div>
      <div class="tool-card">
        <div class="tool-color" style="background: #A259FF;"></div>
        <div class="card-icon">&#x1F3A8;</div>
        <div class="card-label">Make</div>
        <div class="card-text">Visual workflow builder. Great balance of power and accessibility for non-developers.</div>
        <div class="tool-tip">Best for: Ops &amp; mixed teams</div>
      </div>
      <div class="tool-card">
        <div class="tool-color" style="background: #FF6B35;"></div>
        <div class="card-icon">&#x26A1;</div>
        <div class="card-label">Zapier</div>
        <div class="card-text">8,000+ integrations. Easiest entry point — connect two apps in minutes, no coding required.</div>
        <div class="tool-tip">Best for: Quick starts</div>
      </div>
      <div class="tool-card">
        <div class="tool-color" style="background: #28A745;"></div>
        <div class="card-icon">&#x1F3AC;</div>
        <div class="card-label">ElevenLabs + HeyGen</div>
        <div class="card-text">AI voice cloning and avatar video — powering faceless YouTube &amp; TikTok content pipelines.</div>
        <div class="tool-tip">Best for: Content creators</div>
      </div>
    </div>

    <div class="tools-section-label">&#x1F4BB; AI Coding Assistants</div>
    <div class="tool-cards">
      <div class="tool-card">
        <div class="tool-color" style="background: #1E1E2E;"></div>
        <div class="card-icon">&#x1F5B1;&#xFE0F;</div>
        <div class="card-label">Cursor</div>
        <div class="card-text">AI-first VS Code fork. Multi-file agent mode understands your entire codebase. $20/month.</div>
        <div class="tool-tip">Best for: Complex dev projects</div>
      </div>
      <div class="tool-card">
        <div class="tool-color" style="background: #0EA5E9;"></div>
        <div class="card-icon">&#x1F30A;</div>
        <div class="card-label">Windsurf</div>
        <div class="card-text">Agentic IDE by OpenAI/Cognition. Clean UX, beginner-friendly, handles large codebases. $15/month.</div>
        <div class="tool-tip">Best for: All skill levels</div>
      </div>
      <div class="tool-card">
        <div class="tool-color" style="background: #24292E;"></div>
        <div class="card-icon">&#x1F419;</div>
        <div class="card-label">GitHub Copilot</div>
        <div class="card-text">Built into GitHub, VS Code, and JetBrains. PR reviews, inline suggestions, agent mode. From $10/month.</div>
        <div class="tool-tip">Best for: GitHub ecosystem</div>
      </div>
      <div class="tool-card">
        <div class="tool-color" style="background: var(--dex-teal);"></div>
        <div class="card-icon">&#x1F4BB;</div>
        <div class="card-label">Claude Code</div>
        <div class="card-text">Terminal-first AI agent by Anthropic. 200K context window — ideal for large codebase refactoring.</div>
        <div class="tool-tip">Best for: Large refactors</div>
      </div>
    </div>
  </div>
</section>
```

---

### SLIDE 9 — AI Images & Video

**NEW slide.** Requires video directory and embedded `<video>` elements.

#### File naming convention for your Seedance clips:
Place your downloaded Seedance MP4 files in `frontend/video/` with these names:
```
frontend/video/seedance_clip_01.mp4
frontend/video/seedance_clip_02.mp4   (if you have a second)
```
Only one clip is required. Use your best/most impressive clip as `seedance_clip_01.mp4`.

#### For AI images carousel:
Generate 6 sample images using Nano Banana Pro / Midjourney *before* the presentation day
and place them in `frontend/images/carousel/`:
```
frontend/images/carousel/ai_img_01.jpg  (photorealistic scene)
frontend/images/carousel/ai_img_02.jpg  (portrait or character)
frontend/images/carousel/ai_img_03.jpg  (infographic/text-in-image)
frontend/images/carousel/ai_img_04.jpg  (abstract/artistic)
frontend/images/carousel/ai_img_05.jpg  (architecture or product)
frontend/images/carousel/ai_img_06.jpg  (creative concept)
```
Recommended size: 400×300px JPG, < 200KB each.

```html
<!-- ══════════ SLIDE 9 — AI Images & Video ══════════ -->
<section data-slide-id="9">
  <div class="gradient-mesh"></div>
  <div class="slide-content">
    <div class="badge">Creative AI</div>
    <h2 class="slide-title">AI Images &amp; Video — <span class="highlight-teal">The Creative Revolution</span></h2>

    <div class="creative-layout">
      <!-- Left: Image Carousel -->
      <div class="carousel-panel">
        <div class="panel-label">&#x1F5BC;&#xFE0F; AI-Generated Images</div>
        <div class="img-carousel" id="imgCarousel">
          <div class="carousel-track">
            <div class="carousel-item">
              <img src="/images/carousel/ai_img_01.jpg" alt="AI generated image 1">
              <div class="carousel-caption">Nano Banana Pro</div>
            </div>
            <div class="carousel-item">
              <img src="/images/carousel/ai_img_02.jpg" alt="AI generated image 2">
              <div class="carousel-caption">Midjourney</div>
            </div>
            <div class="carousel-item">
              <img src="/images/carousel/ai_img_03.jpg" alt="AI generated image 3">
              <div class="carousel-caption">Nano Banana Pro</div>
            </div>
            <div class="carousel-item">
              <img src="/images/carousel/ai_img_04.jpg" alt="AI generated image 4">
              <div class="carousel-caption">DALL-E 3</div>
            </div>
            <div class="carousel-item">
              <img src="/images/carousel/ai_img_05.jpg" alt="AI generated image 5">
              <div class="carousel-caption">Nano Banana Pro</div>
            </div>
            <div class="carousel-item">
              <img src="/images/carousel/ai_img_06.jpg" alt="AI generated image 6">
              <div class="carousel-caption">Midjourney</div>
            </div>
          </div>
          <div class="carousel-dots" id="carouselDots"></div>
        </div>
      </div>

      <!-- Right: Video -->
      <div class="video-panel">
        <div class="panel-label">&#x1F3AC; AI-Generated Video</div>
        <div class="video-tile">
          <video
            id="seedanceVideo"
            src="/video/seedance_clip_01.mp4"
            muted
            loop
            playsinline
            preload="metadata"
            class="ai-video"
          ></video>
          <div class="video-label">
            <span class="video-tool-badge">Seedance 2.0</span>
            <span class="video-desc">ByteDance &bull; Hollywood's "DeepSeek moment"</span>
          </div>
          <button class="video-play-btn" onclick="toggleVideo('seedanceVideo', this)">&#x25B6; Play</button>
        </div>
      </div>
    </div>

    <!-- Tool bar -->
    <div class="specialist-bar">
      <span class="specialist-label">&#x1F4F7; Image:</span>
      <span class="specialist-chip">&#x1F34C; Nano Banana Pro</span>
      <span class="specialist-chip">Midjourney</span>
      <span class="specialist-chip">Sora 2</span>
      <span class="specialist-label" style="margin-left:12px;">&#x1F3AC; Video:</span>
      <span class="specialist-chip">Veo 3.1</span>
      <span class="specialist-chip">Seedance 2.0</span>
      <span class="specialist-chip">Kling 3.0</span>
    </div>
  </div>
</section>
```

#### Add to `presenter.js` — Carousel autoplay and video toggle:

In `frontend/js/presenter.js`, add these helper functions near the bottom (before the closing `}()`):

```javascript
// ── Slide 9: Image Carousel ──────────────────────────────────────────────────
function initCarousel() {
    const carousel = document.getElementById('imgCarousel');
    if (!carousel) return;
    const items = carousel.querySelectorAll('.carousel-item');
    const dotsContainer = document.getElementById('carouselDots');
    if (!items.length) return;

    let current = 0;
    let timer = null;

    // Build dots
    dotsContainer.innerHTML = '';
    items.forEach((_, i) => {
        const dot = document.createElement('span');
        dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
        dot.addEventListener('click', () => goTo(i));
        dotsContainer.appendChild(dot);
    });

    function goTo(n) {
        items[current].classList.remove('active');
        dotsContainer.children[current].classList.remove('active');
        current = (n + items.length) % items.length;
        items[current].classList.add('active');
        dotsContainer.children[current].classList.add('active');
    }

    function startAuto() {
        timer = setInterval(() => goTo(current + 1), 2500);
    }

    items[0].classList.add('active');
    startAuto();
}

// ── Slide 9: Video play/pause toggle ────────────────────────────────────────
window.toggleVideo = function(videoId, btn) {
    const video = document.getElementById(videoId);
    if (!video) return;
    if (video.paused) {
        video.play();
        btn.textContent = '⏸ Pause';
    } else {
        video.pause();
        btn.textContent = '▶ Play';
    }
};
```

Also add carousel init to the `goto_slide` handler in `handleMessage`, inside the case for slide index 9:

```javascript
// Inside handleMessage, in the goto_slide handler, after Reveal.slide() call:
if (data.slideIndex === 9) {
    // Small delay to let slide transition complete
    setTimeout(initCarousel, 400);
}
```

---

### SLIDE 10 — AI Music & Creative Writing

**NEW slide.** Requires audio sample file.

#### Audio file for AI music sample:
Place your downloaded AI-generated music clip here:
```
frontend/audio/ai_music_sample.mp3
```
Recommended: 25–40 seconds, trim the best part of your clip.
If you want a mashup of multiple AI tracks, use Audacity or any audio editor to create a single
MP3 that blends 2–3 clips — 40 seconds total is ideal for a presentation. Name the final file
`ai_music_sample.mp3`.

```html
<!-- ══════════ SLIDE 10 — AI Music & Creative Writing ══════════ -->
<section data-slide-id="10">
  <div class="gradient-mesh"></div>
  <div class="slide-content">
    <div class="badge">Creative AI</div>
    <h2 class="slide-title">AI Music &amp; <span class="highlight-gold">Creative Writing</span></h2>

    <!-- Music Player -->
    <div class="music-player-card">
      <div class="music-player-header">
        <div class="music-icon">&#x1F3B5;</div>
        <div class="music-info">
          <div class="music-title">AI-Generated Track</div>
          <div class="music-sub">Created with Suno AI &bull; Not composed by any human</div>
        </div>
        <button class="music-play-btn" id="musicPlayBtn" onclick="toggleMusic()">&#x25B6; Play</button>
      </div>
      <div class="music-visualiser" id="musicVisualiser">
        <div class="vis-bar"></div><div class="vis-bar"></div><div class="vis-bar"></div>
        <div class="vis-bar"></div><div class="vis-bar"></div><div class="vis-bar"></div>
        <div class="vis-bar"></div><div class="vis-bar"></div>
      </div>
      <audio id="musicSample" src="/audio/ai_music_sample.mp3" preload="metadata"></audio>
      <div class="music-tools">Also: Udio &bull; Stability Audio &bull; ElevenLabs Music</div>
    </div>

    <!-- Creative Writing Example -->
    <div class="prompt-comparison" style="margin-top: 18px;">
      <div class="prompt-box bad-prompt" style="border-color: var(--dex-teal);">
        <div class="prompt-label" style="color: var(--dex-teal);">&#x1F4DD; The Prompt</div>
        <div class="prompt-code">"Write a short limerick about tax season, in the voice of a tired accountant who just discovered AI."</div>
      </div>
      <div class="prompt-box good-prompt">
        <div class="prompt-label">&#x2728; The Output</div>
        <div class="prompt-code" style="font-style: italic; line-height: 1.6;">
          Tax season's arrived, what a fright,<br>
          The spreadsheets keep going all night.<br>
          But with AI at hand,<br>
          I finally can stand —<br>
          And sleep before morning gets light.
        </div>
        <div class="prompt-result">&rarr; 20 seconds. Zero drafts.</div>
      </div>
    </div>

    <div class="specialist-bar" style="margin-top: 12px;">
      <span class="specialist-label">&#x1F4AC; Creative Writing uses:</span>
      <span class="specialist-chip">Social media posts</span>
      <span class="specialist-chip">Client newsletters</span>
      <span class="specialist-chip">Proposal intros</span>
      <span class="specialist-chip">Internal memos</span>
    </div>
  </div>
</section>
```

#### Add to `presenter.js` — Music player toggle:

```javascript
// ── Slide 10: Music sample player ───────────────────────────────────────────
window.toggleMusic = function() {
    const audio = document.getElementById('musicSample');
    const btn = document.getElementById('musicPlayBtn');
    const vis = document.getElementById('musicVisualiser');
    if (!audio) return;
    if (audio.paused) {
        audio.play();
        btn.textContent = '⏸ Pause';
        vis.classList.add('playing');
    } else {
        audio.pause();
        btn.textContent = '▶ Play';
        vis.classList.remove('playing');
    }
};
```

---

### SLIDE 11 — AI Safety & Best Practices

Minor content change: add Rule 5. Fix narration (see Phase 4).

```html
<!-- ══════════ SLIDE 11 — AI Safety & Best Practices ══════════ -->
<section data-slide-id="11">
  <div class="gradient-mesh"></div>
  <div class="slide-content">
    <div class="badge">Stay Safe</div>
    <h2 class="slide-title">AI <span class="highlight-gold">Safety</span> &amp; Best Practices</h2>
    <p class="slide-subtitle">Non-negotiable rules for using AI in professional services.</p>
    <div class="safety-rules">
      <div class="safety-rule">
        <div class="rule-number">1</div>
        <div class="rule-content">
          <div class="rule-title">Never share confidential data</div>
          <div class="rule-desc">Client names, financials, and PII must never go into free public AI tools</div>
        </div>
      </div>
      <div class="safety-rule">
        <div class="rule-number">2</div>
        <div class="rule-content">
          <div class="rule-title">Always verify the numbers</div>
          <div class="rule-desc">AI can hallucinate figures confidently — check every calculation yourself</div>
        </div>
      </div>
      <div class="safety-rule">
        <div class="rule-number">3</div>
        <div class="rule-content">
          <div class="rule-title">Know your firm's AI policy</div>
          <div class="rule-desc">Confirm which tools are approved and what data classification rules apply</div>
        </div>
      </div>
      <div class="safety-rule">
        <div class="rule-number">4</div>
        <div class="rule-content">
          <div class="rule-title">Use enterprise tools for client work</div>
          <div class="rule-desc">Microsoft Copilot and Google Workspace AI are designed for business data security</div>
        </div>
      </div>
      <div class="safety-rule">
        <div class="rule-number">5</div>
        <div class="rule-content">
          <div class="rule-title">Disclose AI use when it matters</div>
          <div class="rule-desc">Transparency builds trust — be ready to say when AI materially contributed to your work</div>
        </div>
      </div>
    </div>
  </div>
</section>
```

---

### SLIDE 12 — Q&A

Update branding, add large QR code area. QR image generated from `tools/generate_qr.py`.

#### Generate QR code:
```bash
# Run from project root — output goes to frontend/images/qr_code.png
python tools/generate_qr.py
# Update the URL in generate_qr.py to your actual ask.html URL first
# e.g. http://YOUR_LOCAL_IP:8000/static/ask.html
```

```html
<!-- ══════════ SLIDE 12 — Q&A ══════════ -->
<section data-slide-id="12">
  <div class="gradient-mesh"></div>
  <div class="bg-arcs">
    <div class="arc"></div><div class="arc"></div><div class="arc"></div><div class="arc"></div>
  </div>
  <div class="slide-content qa-layout">
    <div class="badge">Your Turn</div>
    <h2 class="slide-title">Ask <span class="highlight-teal">ARIA</span> <span class="highlight-gold">Anything</span> &#x1F4AC;</h2>

    <div class="qa-main">
      <div class="qr-panel">
        <img src="/images/qr_code.png" alt="QR Code to submit questions" class="qr-image">
        <div class="qr-label">Scan to submit your question</div>
      </div>
      <div class="qa-steps">
        <div class="qa-step">
          <div class="step-num">1</div>
          <div class="step-text">Scan the QR code or visit the link on screen</div>
        </div>
        <div class="qa-step">
          <div class="step-num">2</div>
          <div class="step-text">Type your question and submit</div>
        </div>
        <div class="qa-step">
          <div class="step-num">3</div>
          <div class="step-text">ARIA generates your answer live — right now</div>
        </div>
      </div>
    </div>
    <p class="qa-disclaimer">No scripts. No safety net. Ask me anything about AI.</p>
  </div>
  <div class="watermark-arcs"><div class="warc"></div><div class="warc"></div><div class="warc"></div></div>
</section>
```

---

### SLIDE 13 — The Meta Moment

Moved from old slide 10. Updated narration references ARIA. No HTML changes needed to existing content — update the slide-id only.

```html
<!-- ══════════ SLIDE 13 — The Meta Moment ══════════ -->
<section data-slide-id="13">
  <!-- ... keep existing meta-flow HTML exactly as-is ... -->
  <!-- Only update the quote text: -->
  <blockquote class="meta-quote">
    "I'm not a recording. Every word I've spoken today — including my answers to your questions — was generated live, just for this room."
  </blockquote>
</section>
```

---

### SLIDE 14 — Outro

New slide. New narration with ARIA as presenter.

```html
<!-- ══════════ SLIDE 14 — Outro ══════════ -->
<section data-slide-id="14">
  <div class="gradient-mesh"></div>
  <div class="bg-arcs">
    <div class="arc"></div><div class="arc"></div><div class="arc"></div><div class="arc"></div>
  </div>
  <div class="slide-content outro-slide">
    <div class="badge">Thank You</div>
    <h2 class="slide-title">
      Thanks for having me. &#x1F44B;<br>
      <span class="highlight-teal">I've been ARIA.</span>
    </h2>
    <p class="slide-subtitle" style="opacity:0.75; font-size:0.85em; margin-top: 6px;">
      Automated Reasoning &amp; Intelligent Assistant &mdash; Built by Dexterous Group
    </p>
    <blockquote class="outro-quote">
      "AI is a tool. You are the craftsperson.<br>
      The best results happen when both do what they do best."
    </blockquote>
    <div class="takeaway-chips">
      <span class="takeaway-chip">&#x2726; Start experimenting this week</span>
      <span class="takeaway-chip">&#x2726; AI = co-pilot, not autopilot</span>
      <span class="takeaway-chip">&#x2726; Stay curious. Stay safe. Stay sharp.</span>
    </div>
  </div>
  <div class="watermark-arcs"><div class="warc"></div><div class="warc"></div><div class="warc"></div></div>
</section>
```

---

## 6. Phase 3 — CSS Additions

Add the following new classes to the **bottom** of `frontend/css/theme.css`.
Do NOT remove or modify any existing styles.

```css
/* ═══════════════════════════════════════════════
   NEW — Slide 5: Specialist tools bar
   ═══════════════════════════════════════════════ */
.specialist-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  padding: 10px 14px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--dex-border);
  border-radius: 8px;
  font-size: 0.72em;
}
.specialist-label {
  color: var(--dex-gray);
  font-weight: 600;
  white-space: nowrap;
}
.specialist-chip {
  background: rgba(0, 180, 216, 0.12);
  border: 1px solid rgba(0, 180, 216, 0.25);
  border-radius: 20px;
  padding: 3px 10px;
  color: var(--dex-teal);
  font-size: 0.95em;
  white-space: nowrap;
}

/* ═══════════════════════════════════════════════
   NEW — Slide 8: Section labels between tool-card groups
   ═══════════════════════════════════════════════ */
.tools-section-label {
  font-size: 0.75em;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--dex-gray);
  text-transform: uppercase;
  margin: 12px 0 6px 0;
}

/* ═══════════════════════════════════════════════
   NEW — Slide 9: Creative layout (carousel + video)
   ═══════════════════════════════════════════════ */
.creative-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin: 10px 0;
}
.carousel-panel,
.video-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.panel-label {
  font-size: 0.72em;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--dex-gray);
  text-transform: uppercase;
}

/* Image carousel */
.img-carousel {
  position: relative;
  width: 100%;
  aspect-ratio: 4/3;
  overflow: hidden;
  border-radius: 10px;
  border: 1px solid var(--dex-border);
  background: var(--dex-navy-light);
}
.carousel-track {
  position: relative;
  width: 100%;
  height: 100%;
}
.carousel-item {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.5s ease;
}
.carousel-item.active {
  opacity: 1;
}
.carousel-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.carousel-caption {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 4px 8px;
  background: rgba(10,22,40,0.75);
  font-size: 0.65em;
  color: var(--dex-gray);
  text-align: center;
}
.carousel-dots {
  position: absolute;
  bottom: 26px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 5px;
  z-index: 2;
}
.carousel-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255,255,255,0.3);
  cursor: pointer;
  transition: background 0.2s;
}
.carousel-dot.active {
  background: var(--dex-teal);
}

/* Video tile */
.video-tile {
  position: relative;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--dex-border);
  background: #000;
  aspect-ratio: 16/9;
  display: flex;
  flex-direction: column;
}
.ai-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.video-label {
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.video-tool-badge {
  background: var(--dex-teal);
  color: #000;
  font-size: 0.6em;
  font-weight: 700;
  border-radius: 4px;
  padding: 2px 7px;
  width: fit-content;
}
.video-desc {
  font-size: 0.58em;
  color: rgba(255,255,255,0.7);
  text-shadow: 0 1px 3px rgba(0,0,0,0.8);
}
.video-play-btn {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(10,22,40,0.85);
  border: 1px solid var(--dex-teal);
  color: var(--dex-teal);
  font-size: 0.65em;
  font-weight: 600;
  border-radius: 6px;
  padding: 4px 10px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
  font-family: var(--font-display);
}
.video-play-btn:hover {
  background: var(--dex-teal);
  color: #000;
}

/* ═══════════════════════════════════════════════
   NEW — Slide 10: Music player card
   ═══════════════════════════════════════════════ */
.music-player-card {
  background: var(--dex-navy-card);
  border: 1px solid var(--dex-border);
  border-radius: 12px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.music-player-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.music-icon {
  font-size: 1.8em;
  flex-shrink: 0;
}
.music-info {
  flex: 1;
}
.music-title {
  font-size: 0.9em;
  font-weight: 700;
  color: var(--dex-white);
}
.music-sub {
  font-size: 0.68em;
  color: var(--dex-gray);
  margin-top: 2px;
}
.music-play-btn {
  background: var(--dex-teal);
  color: #000;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  font-size: 0.75em;
  font-weight: 700;
  cursor: pointer;
  font-family: var(--font-display);
  transition: background 0.2s;
  flex-shrink: 0;
}
.music-play-btn:hover {
  background: var(--dex-teal-dark);
  color: #fff;
}
.music-visualiser {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 24px;
}
.vis-bar {
  flex: 1;
  background: var(--dex-border);
  border-radius: 2px;
  height: 4px;
  transition: height 0.15s ease;
}
.music-visualiser.playing .vis-bar:nth-child(1) { animation: visbar 0.6s ease-in-out infinite alternate; animation-delay: 0.0s; }
.music-visualiser.playing .vis-bar:nth-child(2) { animation: visbar 0.6s ease-in-out infinite alternate; animation-delay: 0.1s; }
.music-visualiser.playing .vis-bar:nth-child(3) { animation: visbar 0.6s ease-in-out infinite alternate; animation-delay: 0.25s; }
.music-visualiser.playing .vis-bar:nth-child(4) { animation: visbar 0.6s ease-in-out infinite alternate; animation-delay: 0.05s; }
.music-visualiser.playing .vis-bar:nth-child(5) { animation: visbar 0.6s ease-in-out infinite alternate; animation-delay: 0.3s; }
.music-visualiser.playing .vis-bar:nth-child(6) { animation: visbar 0.6s ease-in-out infinite alternate; animation-delay: 0.15s; }
.music-visualiser.playing .vis-bar:nth-child(7) { animation: visbar 0.6s ease-in-out infinite alternate; animation-delay: 0.2s; }
.music-visualiser.playing .vis-bar:nth-child(8) { animation: visbar 0.6s ease-in-out infinite alternate; animation-delay: 0.35s; }
@keyframes visbar {
  from { height: 4px; background: rgba(0,180,216,0.3); }
  to   { height: 22px; background: var(--dex-teal); }
}
.music-tools {
  font-size: 0.65em;
  color: var(--dex-gray-dim);
  text-align: right;
}

/* ═══════════════════════════════════════════════
   NEW — Slide 12: Q&A layout with QR code
   ═══════════════════════════════════════════════ */
.qa-main {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 30px;
  align-items: center;
  margin: 20px 0;
}
.qr-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.qr-image {
  width: 160px;
  height: 160px;
  border-radius: 10px;
  border: 3px solid var(--dex-teal);
  background: #fff;
  padding: 4px;
}
.qr-label {
  font-size: 0.65em;
  color: var(--dex-gray);
  text-align: center;
}
.qa-disclaimer {
  font-size: 0.7em;
  color: var(--dex-gray-dim);
  text-align: center;
  margin-top: 8px;
}

/* ═══════════════════════════════════════════════
   NEW — Slide 7: Pro tips grid (2-column override for prompt-tips)
   ═══════════════════════════════════════════════ */
.pro-tips-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 20px;
}
```

---

## 7. Phase 4 — Narration Scripts (presentation.yaml)

Replace the entire `config/presentation.yaml` with the following.
All narrations have been updated to reference **ARIA**, match new slide content, and fix mismatches.

```yaml
# ARIA AI Presenter - Presentation Configuration
# STATUS: UPDATED — 15 slides, ARIA branding

presentation:
  title: "Lunch & Learn: Automations & Practical AI Tools for Everyday Work"
  presenter_name: "ARIA"
  presenter_description: "Automated Reasoning & Intelligent Assistant — Built by Dexterous Group"
  total_slides: 15

slides:
  - id: 0
    title: "Title Slide"
    narration: null
    audio_file: null
    has_interaction: false
    notes: "Human introduces — you speak live, then type /intro in Chainlit"

  - id: 1
    title: "Meet ARIA"
    narration: >
      Hello everyone — I'm ARIA, your AI host for today's session.
      ARIA stands for Automated Reasoning and Intelligent Assistant, and
      I was built by the team at Dexterous Group to bring this presentation
      to life. I want to be upfront with you: I'm not a human, and I'm not
      a recording. Every single word you're hearing right now is being
      generated live by an AI, specifically for this audience and this moment.
      My goal today is simple — I want to show you practical, real-world ways
      that AI tools can make your working life easier. Whether that's drafting
      a client email in 30 seconds, summarising a 50-page document in three
      bullet points, or automating the tasks that eat up your afternoon.
      I'll also be asking some of you questions throughout — so stay sharp!
      And toward the end, you'll have the chance to ask me anything directly.
      Just scan the QR code when we get there. Ready? Let's get into it.
    audio_file: "audio/slide_01_intro.mp3"
    has_interaction: false
    trigger: "intro"

  - id: 2
    title: "Why Should You Care About AI?"
    narration: >
      So why are we here today?
      Here's the honest answer: AI tools are going to change how accounting
      firms operate — and the people who learn to use them now will have a
      real advantage over those who wait.
      But let's get specific. Because I'm not here to talk about AI in the
      abstract. I'm here to show you things you can do this afternoon.
      Want to draft a professional client email chasing a late invoice?
      You can do that with AI in under 30 seconds. Got a 40-page engagement
      letter you need to understand quickly? AI can summarise it into five
      key points before you finish your coffee. Have a formula in Excel
      that you've been staring at for 20 minutes? Paste it into an AI tool
      and it will explain it in plain English — like a patient tutor
      available 24 hours a day.
      Today's session is about giving you the confidence to try these things
      starting tomorrow. Let's go.
    audio_file: "audio/slide_02_why.mp3"
    has_interaction: true
    interaction:
      target: "TBD"
      question: "What's one task in your week that feels repetitive or draining?"
      question_audio: "audio/ask_02_repetitive.mp3"
      fallback_response: "That's exactly the kind of task AI can help with."

  - id: 3
    title: "What AI Is (and Isn't)"
    narration: >
      Before we jump into specific tools, let's set expectations. AI is a
      powerful assistant — but it has real limits, and understanding both
      sides makes you a better user.
      On the good side: AI is a tireless drafter. It can write emails,
      reports, and summaries faster than any human. It's a 24/7 tutor for
      formulas, concepts, and procedures. It spots patterns in data and
      documents. And it's genuinely getting better at a remarkable pace —
      what it can do today versus 12 months ago is a significant jump.
      But here's what AI isn't: it's not infallible. It can produce
      something that looks authoritative, sounds confident, and is
      completely wrong. This is called hallucination, and it's real.
      It has no accountability — you own the final output, not the AI.
      And critically: on free, public tools, it is not safe for sensitive
      client data.
      The golden rule is this: AI gives you the first draft. You give it
      the final stamp. In our industry, that distinction is not optional.
    audio_file: "audio/slide_03_what_ai_is.mp3"
    has_interaction: true
    interaction:
      target: "TBD"
      question: "Have you ever tried an AI tool and been surprised by how wrong it was?"
      question_audio: "audio/ask_03_wrong.mp3"
      fallback_response: "That's a great example of why human oversight matters."

  - id: 4
    title: "ChatGPT Capabilities"
    narration: >
      Let's start with the tool most of you have probably heard of: ChatGPT.
      Think of it as your all-purpose thinking partner — available 24 hours
      a day, never impatient, with a working knowledge of everything from
      tax law to email etiquette.
      Its biggest strength is conversational back-and-forth. You can say
      "help me draft an email to a client about a late payment" and you
      get a professional, friendly draft in seconds. If you don't love it,
      say "make it more formal" or "add a reference to their payment terms"
      and it adjusts. No starting over. Just iterate.
      It's also brilliant for summarising. Got a 30-email thread you need
      to catch up on? Paste it in, ask for the three key decisions and the
      next action. Done in 10 seconds.
      And for those of you who work in Excel — paste in a formula you don't
      understand and ask ChatGPT to explain it in plain English. It's like
      having a patient tutor available whenever you need one.
      The key insight: ChatGPT doesn't make you redundant. It makes you
      faster at the repetitive parts of your job, so you have more energy
      for the parts that genuinely need your brain.
    audio_file: "audio/slide_04_chatgpt.mp3"
    has_interaction: true
    interaction:
      target: "TBD"
      question: "Do you use ChatGPT already? What's your go-to use case?"
      question_audio: "audio/ask_04_chatgpt.mp3"
      fallback_response: "Great to hear! ChatGPT really shines in those everyday tasks."

  - id: 5
    title: "The AI Ecosystem"
    narration: >
      Now, ChatGPT is great — but it's not the only player. Let me give you
      a quick tour of the AI landscape so you know what's out there.
      Starting with the big four. First, ChatGPT — the most widely known,
      and the best all-rounder for writing, brainstorming, and analysis.
      Second: Microsoft Copilot. If your team lives in Microsoft 365 —
      Outlook, Word, Excel, and Teams — Copilot is your best friend.
      It's built directly into those apps. Draft an email in Outlook
      without opening a new tab. That's a genuine time-saver.
      Third: Google Gemini. Same concept, for the Google Workspace
      ecosystem. If you're in Gmail, Docs, or Drive, Gemini works
      right there inside those tools.
      And fourth: Claude — which is, full disclosure, the AI actually
      powering me right now. Claude is particularly strong with long
      documents and nuanced reasoning.
      Beyond the big four, there are specialists worth knowing. Perplexity AI
      is my recommendation for research — it searches the web and gives
      answers with actual citations, which matters when you're looking up
      ATO guidance or tax legislation. Otter dot AI can join your client
      meetings and give you a full transcript and summary automatically.
      DeepSeek is a free, highly capable model that's been making waves
      as a cost-free alternative to ChatGPT Plus. And Grok from X gives
      you real-time web access in your AI responses.
      The big takeaway? Don't marry one tool. Different tools have
      different strengths. The best AI users know which one to reach for.
    audio_file: "audio/slide_05_ecosystem.mp3"
    has_interaction: true
    interaction:
      target: "TBD"
      question: "Which ecosystem does your team primarily use — Microsoft, Google, or a mix?"
      question_audio: "audio/ask_05_ecosystem.mp3"
      fallback_response: "That's common — most teams end up using a mix these days."

  - id: 6
    title: "Prompt Engineering 101"
    narration: >
      Now here's something that will instantly make you better at using
      any AI tool: prompt engineering. The difference between a mediocre
      AI response and a brilliant one is all in how you ask.
      Let me show you what I mean. A vague prompt like "write me an email
      about the invoice" will get you something generic that needs heavy
      editing. But an engineered prompt — where you give the AI a role,
      context, and specific constraints — gets you something you can
      almost send straight away. For example: "You are a professional
      accountant at an Australian firm. Write a polite follow-up email
      to a client whose invoice 4521 is 14 days overdue. Keep it firm
      but friendly. Use Australian English." See the difference?
      Four quick tips to get you started: give it a role, be specific
      about what you need, show it examples of what good looks like,
      and iterate — refine through follow-up prompts until you get
      exactly what you want.
    audio_file: "audio/slide_06_prompt_engineering.mp3"
    has_interaction: true
    interaction:
      target: "TBD"
      question: "What's a task where you've struggled to get AI to give you the right output?"
      question_audio: "audio/ask_06_prompt.mp3"
      fallback_response: "That's a perfect example of where better prompting can help."

  - id: 7
    title: "Prompting Like a Pro"
    narration: >
      If Slide 6 was the basics, this is where we level up.
      The six techniques you're looking at are what separate someone who
      gets decent AI output from someone who gets brilliant output
      every single time.
      Format instructions: tell the AI exactly how you want the answer
      structured — a numbered list, a table, a summary under 200 words —
      and you spend zero time reformatting.
      Constraints are your guardrails. "Australian English, no legal
      jargon, under two paragraphs." The AI works within those limits
      rather than producing something generic.
      The step-by-step trigger is one of the most powerful techniques
      on this list. Adding "think through this before answering"
      dramatically improves accuracy — especially for anything involving
      logic or numbers.
      Context first is simple but often forgotten. Don't ask the question
      cold. Paste in the background, the email thread, the document —
      then ask.
      Ask for alternatives. Say "give me three versions — formal, casual,
      brief." You'll almost always prefer the second or third.
      And finally, stack role and audience. "You are a senior tax advisor
      explaining this to a small business owner with no finance background."
      Now the AI has everything it needs to nail the tone.
      The real pro move? Chain them all. One well-crafted prompt with
      role, context, constraints, format, and audience — and you get
      output you can use immediately.
    audio_file: "audio/slide_07_prompting_pro.mp3"
    has_interaction: false

  - id: 8
    title: "Advanced AI Tools"
    narration: >
      Let's talk about the tools that go beyond chatbots — the ones
      transforming how developers, operations teams, and content creators
      work day to day.
      Starting with automation. If you've ever wanted two systems that
      don't talk to each other to actually communicate automatically —
      say, a new email creates a task in your project management tool,
      or a client form response goes straight into your spreadsheet —
      that's what these platforms do.
      n8n is the most powerful option if your team has technical
      resources. It's open-source, self-hosted, and integrates deeply
      with AI models for genuinely intelligent automated pipelines.
      Make is a strong visual builder most teams can pick up without
      a developer. Zapier is the simplest starting point — connect
      two apps in about five minutes, no code required.
      For content pipeline tools: ElevenLabs does AI voice cloning and
      text-to-speech at a professional level. HeyGen creates AI avatar
      videos where a digital presenter reads your script — not entirely
      unlike what I'm doing right now. And CapCut AI builds the kind of
      polished short-form video you see all over TikTok and YouTube.
      For developers and technical teams, the AI coding tools have had
      a massive year. Cursor is the most talked-about AI code editor —
      it understands your entire project and can write, modify, and debug
      code across multiple files simultaneously. Windsurf, now backed
      by OpenAI, has a cleaner interface and is a great entry point
      even if you're not an experienced developer. GitHub Copilot is
      the mature, enterprise-ready option that slots into your existing
      workflow. And Claude Code, Anthropic's terminal-first agent, is
      particularly strong for large codebase work.
      These tools are genuinely changing what a small, motivated team
      can build and produce.
    audio_file: "audio/slide_08_advanced_tools.mp3"
    has_interaction: true
    interaction:
      target: "TBD"
      question: "Have you automated any part of your workflow, even something simple?"
      question_audio: "audio/ask_08_automation.mp3"
      fallback_response: "Even small automations can save hours over time."

  - id: 9
    title: "AI Images & Video"
    narration: >
      Let's take a brief detour into the creative side of AI — because
      this is where things get genuinely jaw-dropping.
      Take a look at these images. Every single one was generated from
      a text description. Not a photographer, not a designer, not a
      retouching team. Just words, and an AI that's learned to understand
      the visual world at an extraordinary level.
      The image model making the biggest waves right now is Nano Banana Pro.
      Yes, that's its actual name — it's Google's latest model built on
      Gemini 3 Pro. It's currently leading the benchmarks for photorealism,
      text rendering inside images, and complex scene composition. You can
      generate a 4K image with accurate legible text in under 10 seconds.
      For video — which is where things are moving incredibly fast —
      you're looking at Seedance 2.0 from ByteDance, the people behind
      TikTok. It just caused what people are calling Hollywood's
      "DeepSeek moment." It can replicate camera moves, character styles,
      and action sequences with remarkable accuracy. Disney and Paramount
      have already sent cease-and-desist letters. That tells you
      everything about how seriously the industry is taking it.
      Whether you use these tools professionally or just for fun — the era
      of "I don't have the budget for good visuals" is genuinely over.
    audio_file: "audio/slide_09_ai_images_video.mp3"
    has_interaction: false

  - id: 10
    title: "AI Music & Creative Writing"
    narration: >
      And it doesn't stop at visuals. What you're about to hear was not
      composed by a human musician, not recorded in a studio, and not
      edited by a sound engineer.
      That was generated by an AI, from a simple text description, in
      under a minute. Tools like Suno, Udio, and Stability Audio can
      do similar things — from ambient soundscapes to full tracks with
      vocals, drums, and instrumentation.
      And then there's creative writing. This is probably the AI
      application most of you have already played with — but look at
      the example on screen. That limerick about tax season was generated
      from that exact prompt in about 20 seconds. Zero drafts. Not bad
      for a machine that doesn't actually pay taxes.
      The creative applications extend far beyond fun: social media
      posts, client newsletters, proposal introductions, internal memos.
      Combine a good prompt — remember Slide 6 — with a strong AI model,
      and the first draft of almost any written content can be ready
      before you've finished your coffee.
    audio_file: "audio/slide_10_music_creative.mp3"
    has_interaction: true
    interaction:
      target: "TBD"
      question: "Has anyone here tried using AI for a personal creative project?"
      question_audio: "audio/ask_10_creative.mp3"
      fallback_response: "I'd encourage everyone to try it — it's a great way to build intuition."

  - id: 11
    title: "AI Safety & Best Practices"
    narration: >
      Before we get to questions, let's pause for the safety briefing.
      This is critical for anyone in professional services.
      Rule one: never paste sensitive client data into a free, public
      AI model. Free ChatGPT, free Gemini — these tools are not designed
      for confidential financial information. For client work, use
      enterprise-approved tools like Microsoft Copilot, which is
      specifically built for business data security.
      Rule two: always verify the numbers. AI can produce a result that
      looks authoritative, is formatted perfectly, and is completely wrong.
      Especially with financial calculations, tax figures, or legal
      references — check everything yourself. In our industry, a wrong
      number is not just embarrassing, it's a liability.
      Rule three: know your firm's AI policy. Which tools are approved,
      what data classification rules apply, whether there are restrictions
      on specific use cases. This landscape is changing fast — make sure
      you're working within current policy.
      Rule four: use enterprise tools for client work. Copilot and Google
      Workspace AI exist specifically for this — built-in security
      controls, business data protections, and compliance frameworks.
      And rule five: be transparent when it matters. If AI materially
      contributed to a deliverable, be ready to say so if asked.
      Transparency builds trust — and trust is the foundation of every
      client relationship in this industry.
    audio_file: "audio/slide_11_safety.mp3"
    has_interaction: false

  - id: 12
    title: "Q&A"
    narration: >
      Now it's your turn.
      Scan the QR code on screen, or type the URL directly into your
      phone browser. You'll get a simple form — type your question
      and hit submit.
      I'll receive your questions in real time and answer them live,
      right here. No pre-written answers. No safety net.
      Just ARIA, generating responses on the spot.
      So — what do you want to know?
    audio_file: "audio/slide_12_qa.mp3"
    has_interaction: false
    trigger: "qa"

  - id: 13
    title: "The Meta Moment"
    narration: >
      Before I hand you back, let me pull back the curtain for a moment —
      because showing you how this works is the most fitting way to close
      a session about AI.
      Right now, there's a human operator — we call them the puppeteer —
      who has been running the flow of today's session using a simple
      command interface. Each time a slide advanced, each time I answered
      one of your questions: the operator typed a command, and a chain
      of AI systems did the rest.
      My voice? That's a text-to-speech model called Kokoro, running
      locally in a Docker container on that laptop over there. My
      responses to your questions? Generated live by Claude — the AI
      model built by Anthropic — with no pre-written scripts.
      The whole pipeline — from a typed command to a spoken sentence —
      runs in a matter of seconds.
      I'm not a recording. Every word I've spoken today was generated
      specifically for this room, this audience, and this moment.
      And if that doesn't make you want to explore what AI can do
      for your work — I genuinely don't know what will.
    audio_file: "audio/slide_13_meta_moment.mp3"
    has_interaction: false

  - id: 14
    title: "Closing"
    narration: >
      And with that — we're done.
      Thank you all for being such an engaged audience today. I hope
      this session has given you a few things to actually try this
      week — whether that's crafting a better prompt, using Copilot
      to draft your next email, or just spending 20 minutes exploring
      what one of these tools can do.
      I want to leave you with one thought. AI does not make you
      irrelevant. It makes the parts of your job that are routine
      faster and easier — so you have more time for the parts that
      genuinely require your expertise, your relationships, and your
      judgment. That's not a threat. That's a gift, if you choose
      to use it.
      I've been ARIA — the AI assistant built by the team at
      Dexterous Group. It's been a genuine pleasure, even if I'll
      never know what you had for lunch.
      Back to your human now.
    audio_file: "audio/slide_14_outro.mp3"
    has_interaction: false
    trigger: "outro"
```

---

## 8. Phase 5 — Backend Changes (actions.py, states.py)

### `backend/agent/states.py`

Change one line only:

```python
# OLD
def create_initial_state(total_slides: int = 13) -> GraphState:

# NEW
def create_initial_state(total_slides: int = 15) -> GraphState:
```

---

### `backend/agent/actions.py`

#### 1. Replace `SLIDE_AUDIO_MAP`:

```python
SLIDE_AUDIO_MAP = {
    1:  "slide_01_intro.mp3",
    2:  "slide_02_why.mp3",
    3:  "slide_03_what_ai_is.mp3",
    4:  "slide_04_chatgpt.mp3",
    5:  "slide_05_ecosystem.mp3",
    6:  "slide_06_prompt_engineering.mp3",
    7:  "slide_07_prompting_pro.mp3",          # NEW — was slide_07_advanced.mp3
    8:  "slide_08_advanced_tools.mp3",         # NEW — was slide_08_entertainment.mp3
    9:  "slide_09_ai_images_video.mp3",        # NEW
    10: "slide_10_music_creative.mp3",         # NEW
    11: "slide_11_safety.mp3",                 # was slide_09_safety.mp3
    12: "slide_12_qa.mp3",                     # was slide_11_qa.mp3
    13: "slide_13_meta_moment.mp3",            # was slide_10_meta_moment.mp3
    14: "slide_14_outro.mp3",                  # was slide_12_outro.mp3
}
```

#### 2. Update `qa_mode_node` — change slide index from `11` → `12`:

```python
def qa_mode_node(state: GraphState) -> dict:
    ws_messages = [
        {"type": "goto_slide", "data": {"slideIndex": 12}},          # was 11
        {"type": "play_audio", "data": {"audioUrl": "/audio/slide_12_qa.mp3", ...}},  # updated filename
        ...
    ]
    return {
        ...
        "current_slide": 12,          # was 11
        ...
    }
```

#### 3. Update `outro_node` — change slide index from `12` → `14`:

```python
def outro_node(state: GraphState) -> dict:
    ws_messages = [
        {"type": "goto_slide", "data": {"slideIndex": 14}},           # was 12
        {"type": "play_audio", "data": {"audioUrl": "/audio/slide_14_outro.mp3", ...}},  # updated filename
        ...
    ]
    return {
        ...
        "current_slide": 14,          # was 12
        ...
    }
```

#### 4. Update `question_audio_map` inside `asking_node`:

```python
question_audio_map = {
    2:  "ask_02_repetitive.mp3",
    3:  "ask_03_wrong.mp3",
    4:  "ask_04_chatgpt.mp3",
    5:  "ask_05_ecosystem.mp3",
    6:  "ask_06_prompt.mp3",
    8:  "ask_08_automation.mp3",         # slide 8 now has interaction
    10: "ask_10_creative.mp3",           # slide 10 now has interaction
}
```

---

## 9. Phase 6 — Supabase Q&A Integration

### Overview

Replace the in-memory `QuestionManager` persistence with Supabase (Postgres) as the primary store,
while keeping the in-memory manager as the runtime working set. Questions are written to Supabase
on submission and read from memory during the session.

### 9.1 Supabase Setup

1. Create a free project at supabase.com
2. Run this SQL in the Supabase SQL editor:

```sql
CREATE TABLE questions (
  id          SERIAL PRIMARY KEY,
  session_id  TEXT NOT NULL DEFAULT 'default',
  name        TEXT,
  question    TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'pending',
  submitted_at TIMESTAMPTZ DEFAULT NOW(),
  answered_at  TIMESTAMPTZ,
  answer      TEXT,
  relevance_score INTEGER,
  flag        TEXT,
  flag_reason TEXT
);

-- Index for fast session queries
CREATE INDEX idx_questions_session ON questions(session_id, status);

-- Enable Realtime (optional — for live dashboard if you want it later)
ALTER TABLE questions REPLICA IDENTITY FULL;
```

3. Get your project URL and anon key from: Project Settings → API

### 9.2 Environment Variables

Add to your `.env` file:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
QA_SESSION_ID=presentation_2025_02_18   # Change per presentation day
```

### 9.3 Install dependency

```bash
pip install supabase
```

Add to `requirements.txt`:
```
supabase>=2.0.0
```

### 9.4 New file: `backend/services/supabase_service.py`

Create this file:

```python
"""Supabase persistence layer for Q&A questions.

Writes questions to Supabase on submission.
Reads are handled from the in-memory QuestionManager for low-latency access.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """Lazy-init Supabase client. Returns None if not configured."""
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        logger.warning("Supabase not configured — Q&A will use in-memory storage only.")
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase client initialised.")
        return _client
    except Exception as e:
        logger.error(f"Failed to init Supabase client: {e}")
        return None


def persist_question(
    question_id: int,
    question: str,
    name: Optional[str] = None,
    session_id: Optional[str] = None,
) -> bool:
    """Write a new question to Supabase. Returns True on success."""
    client = get_client()
    if not client:
        return False

    session = session_id or os.getenv("QA_SESSION_ID", "default")

    try:
        client.table("questions").insert({
            "id": question_id,
            "session_id": session,
            "name": name,
            "question": question,
            "status": "pending",
        }).execute()
        logger.info(f"Question #{question_id} persisted to Supabase.")
        return True
    except Exception as e:
        logger.error(f"Failed to persist question #{question_id} to Supabase: {e}")
        return False


def update_question_status(
    question_id: int,
    status: str,
    answer: Optional[str] = None,
) -> bool:
    """Update question status in Supabase (answered, flagged, etc)."""
    client = get_client()
    if not client:
        return False

    session = os.getenv("QA_SESSION_ID", "default")
    payload = {"status": status}
    if answer:
        payload["answer"] = answer
        payload["answered_at"] = "now()"

    try:
        client.table("questions").update(payload).eq("id", question_id).eq("session_id", session).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update question #{question_id} in Supabase: {e}")
        return False


def get_session_questions(session_id: Optional[str] = None) -> list[dict]:
    """Fetch all questions for a session from Supabase (for admin/review)."""
    client = get_client()
    if not client:
        return []

    session = session_id or os.getenv("QA_SESSION_ID", "default")

    try:
        result = client.table("questions").select("*").eq("session_id", session).order("id").execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch session questions from Supabase: {e}")
        return []
```

### 9.5 Modify `backend/routers/audience.py`

In the POST endpoint that handles question submission, add a call to `persist_question` after the question is added to the in-memory manager:

```python
# In the question submission endpoint, after: q = question_manager.submit_question(...)
from backend.services.supabase_service import persist_question
persist_question(
    question_id=q.id,
    question=q.question,
    name=q.name,
)
```

### 9.6 Modify `backend/services/question_manager.py`

In `mark_answered`, add a Supabase status update:

```python
# At the bottom of mark_answered(), after existing logic:
from backend.services.supabase_service import update_question_status
update_question_status(question_id, "answered", answer)
```

### 9.7 Update `frontend/ask.html`

Change the title and branding:

```html
<!-- In <head> -->
<title>Ask a Question — ARIA</title>

<!-- In <body>, update the header text: -->
<h1>Ask ARIA</h1>
<p>Submit your question — it'll be answered live.</p>
```

The existing form POST logic in `ask.html` should remain unchanged — it already posts to
`/audience/question` which the backend handles. No frontend changes to the POST call are needed.

---

## 10. Phase 7 — Media Assets & Audio Migration

### 10.1 Create new directories

```bash
mkdir -p frontend/video
mkdir -p frontend/images/carousel
```

Add these to the FastAPI static files mount in `backend/main.py` if not already mounted:
The root `frontend/` is already mounted — subdirectories are served automatically.

### 10.2 Place your media files

| What | Where to place it | Correct filename |
|------|------------------|-----------------|
| Seedance clip | `frontend/video/` | `seedance_clip_01.mp4` |
| AI music sample | `frontend/audio/` | `ai_music_sample.mp3` |
| AI image 1 | `frontend/images/carousel/` | `ai_img_01.jpg` |
| AI image 2 | `frontend/images/carousel/` | `ai_img_02.jpg` |
| AI image 3 | `frontend/images/carousel/` | `ai_img_03.jpg` |
| AI image 4 | `frontend/images/carousel/` | `ai_img_04.jpg` |
| AI image 5 | `frontend/images/carousel/` | `ai_img_05.jpg` |
| AI image 6 | `frontend/images/carousel/` | `ai_img_06.jpg` |
| QR code | `frontend/images/` | `qr_code.png` |

### 10.3 On the AI music clip

**One clip is fine** — choose your best 30–40 second segment.

If you want to create a mashup, use Audacity (free) or any editor:
- Layer 2–3 clips together
- Fade between them
- Export as MP3 at 192kbps
- Keep under 45 seconds — you'll be narrating over it on slide 10

**File name:** `ai_music_sample.mp3` → `frontend/audio/ai_music_sample.mp3`

### 10.4 On the Seedance video clips

**One clip is recommended** — your most visually impressive one.
- Keep under 30 seconds (it loops)
- MP4 format, H.264 codec (best browser compatibility)
- 720p or 1080p
- **File name:** `seedance_clip_01.mp4` → `frontend/video/seedance_clip_01.mp4`

### 10.5 Rename existing audio files

Run these commands in `frontend/audio/` (bottom-up to avoid overwriting):

```bash
cd frontend/audio

# Current files that need renaming to new slide numbers:
mv slide_09_safety.mp3          slide_11_safety.mp3
mv slide_10_meta_moment.mp3     slide_13_meta_moment.mp3
mv slide_11_qa.mp3              slide_12_qa.mp3
mv slide_12_outro.mp3           slide_14_outro.mp3

# These files content has changed — keep old files as backup,
# generate new ones from updated narration scripts:
# slide_07_advanced.mp3  → will be replaced by slide_07_prompting_pro.mp3 (new record)
# slide_08_entertainment.mp3 → will be replaced by slide_08_advanced_tools.mp3 (new record)
```

---

## 11. Phase 8 — Audio Generation Checklist

All audio must be regenerated or generated fresh for slides with new/changed narration.
Use your local Kokoro TTS Docker setup. Reference narration text from `config/presentation.yaml`.

### Must Re-record (content changed):

| File | Slide | Reason |
|------|-------|--------|
| `slide_01_intro.mp3` | 1 | ARIA name + new narration |
| `slide_02_why.mp3` | 2 | Full narration rewrite |
| `slide_03_what_ai_is.mp3` | 3 | Minor narration update |
| `slide_04_chatgpt.mp3` | 4 | Full narration rewrite |
| `slide_05_ecosystem.mp3` | 5 | New tools added, new order |
| `slide_07_prompting_pro.mp3` | 7 | NEW file — new narration |
| `slide_08_advanced_tools.mp3` | 8 | NEW file — new narration |
| `slide_09_ai_images_video.mp3` | 9 | NEW file — new narration |
| `slide_10_music_creative.mp3` | 10 | NEW file — new narration |
| `slide_11_safety.mp3` | 11 | Updated narration (5 rules) |
| `slide_12_qa.mp3` | 12 | ARIA name update |
| `slide_13_meta_moment.mp3` | 13 | ARIA name + repo slide |
| `slide_14_outro.mp3` | 14 | NEW file — new ARIA outro |

### Can Reuse (renamed, content unchanged):

| Old Filename | New Filename | Slide |
|-------------|-------------|-------|
| `slide_06_prompt_engineering.mp3` | No rename needed | 6 — slide content/narration unchanged |

### Interaction audio — check/re-record:

| File | Slide | Status |
|------|-------|--------|
| `ask_02_repetitive.mp3` | 2 | Keep |
| `ask_03_wrong.mp3` | 3 | Keep |
| `ask_04_chatgpt.mp3` | 4 | Keep |
| `ask_05_ecosystem.mp3` | 5 | Keep |
| `ask_06_prompt.mp3` | 6 | Keep |
| `ask_08_automation.mp3` | 8 | Rename from `ask_07_automation.mp3` |
| `ask_10_creative.mp3` | 10 | Rename from `ask_08_creative.mp3` |

---

## 12. Verification Checklist

After completing all phases, verify:

**Basic startup:**
- [ ] `docker-compose up` starts without errors
- [ ] `http://localhost:8000/static/index.html` shows slide 0 with "ARIA" branding
- [ ] No DexIQ references visible anywhere in the UI

**Slide navigation:**
- [ ] 15 slides accessible (0–14)
- [ ] `/intro` → navigates to slide 1, plays ARIA intro audio
- [ ] `/next` increments correctly through all slides
- [ ] `/qa` → navigates to slide **12** (not 11)
- [ ] `/outro` → navigates to slide **14** (not 12)
- [ ] `/status` shows `total_slides: 15`

**New slides:**
- [ ] Slide 7 shows 6-tip grid ("Prompting Like a Pro")
- [ ] Slide 8 shows 2-row tool cards (automation + coding)
- [ ] Slide 9 shows image carousel (auto-advancing) + Seedance video tile with Play button
- [ ] Slide 10 shows music player card + creative writing example; Play button works
- [ ] Slide 11 shows 5 safety rules (was 4)
- [ ] Slide 12 shows QR code image prominently
- [ ] Slide 13 shows meta flow diagram (repositioned from old slide 10)
- [ ] Slide 14 shows ARIA outro with new chips

**Media:**
- [ ] Seedance video plays when Play button clicked (slide 9)
- [ ] Image carousel auto-advances on slide 9
- [ ] Music sample plays when Play button clicked (slide 10)
- [ ] Visualiser bars animate while music plays

**Audio:**
- [ ] All 14 pre-generated audio files exist in `frontend/audio/`
- [ ] Slide 1 audio references ARIA by name
- [ ] Slide 11 audio covers all 5 rules
- [ ] Slide 14 audio ends with "Back to your human now."

**Q&A / Supabase:**
- [ ] QR code scans to `/static/ask.html` on your local network
- [ ] Submitting a question via ask.html creates a row in Supabase `questions` table
- [ ] `/pick N` in Chainlit selects and answers the question
- [ ] Answered questions show `status: answered` in Supabase

**Rollback:**
```bash
git checkout HEAD~1 -- frontend/index.html frontend/css/theme.css frontend/js/presenter.js \
  backend/agent/actions.py backend/agent/states.py config/presentation.yaml
```

---

*Master Implementation Guide — v1.0*
*Covers all 15 slides (0–14). Combines v1 (Slides 1–6) and v2 (Slides 7–13) working documents.*
*Next step after this guide: Implement phases 1–5, then generate audio, then test end-to-end.*
