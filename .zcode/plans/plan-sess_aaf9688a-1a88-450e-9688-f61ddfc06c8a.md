# DeepDive UX Overhaul — "Any topic becomes an animated quest"

## Core idea / USP
Stop showing the agent's guts. The user never sees "Diagnose / Plan" screens again. Instead: a playful **3-question MCQ warm-up** → the app silently runs the whole agent pipeline behind a "forging your path" animation → the user gets a **visual lesson** and a **per-topic animated scene** the LLM choreographs as a "scene script" that our CSS/Framer-Motion engine performs. Text-only screens are replaced with interactive scenes, prediction moments, XP/mastery meters, and a shareable mastery card. That's the pitch: *Wikipedia is text; DeepDive turns any concept into an interactive animation that adapts to your misconceptions.*

---

## Backend changes (surgical — state machine and eval scripts untouched)

### 1. Diagnostic MCQ quiz (`schemas.py`, `domain.py`, `agents.py`, `orchestrator.py`)
- New `QuizQuestion {question, options[3-4], correct_index, misconception_tag, explanation}`.
- `TopicBlueprint` gets `diagnostic_quiz: List[QuizQuestion]`; `topic_synthesis_agent` prompt extended to emit it; deterministic fallback builds a generic 3-question quiz.
- Static quizzes for the 6 curated DSA topics in `domain.py` (hand-written, targeting known misconceptions, e.g. "Does the hash map sort the array?" for two-sum).
- `start_session` puts it at `metadata["diagnostic_quiz"]` for both curated + custom topics. User's MCQ picks are serialized to text and fed to the existing `diagnostic_agent_real` via the first `advance` — diagnosis pipeline unchanged.

### 2. Scene script engine data (`schemas.py`, `agents.py`)
Add to `VisualizationSpec` an optional rich `scene` (old `entities/states` kept for backward compat so eval scripts stay green):
- `SceneActor {id, kind, label, icon(emoji), x, y, color?, value?}` — kinds: `box|token|node|sun|drop|bubble|arrow|counter|chip|meter|lane|creature|stack`. x/y are 0–100 grid coords.
- `SceneStep {id, caption, effects: [SceneEffect]}`, `SceneEffect {actor, action, to_x?, to_y?, value?, label?}` — actions: `appear|disappear|move|pulse|shake|split|merge|fill|increment|highlight|dim|connect|emit`.
- Both visualization agents get prompt guidance + schema to emit 4–8 grounded steps; deterministic **fallback scene builder** (from `example_values`/`example_walkthrough`) covers LLM/JSON failures so the stage never breaks.
- Photosynthesis example: sun actor emits photon tokens → drop splits into bubble(O2)+electron tokens → energy tokens flow into a "Calvin cycle" node → glucose counter increments. Two-sum: array boxes + pointer + map chips filling. Per-topic, zero hardcoded scenes.

### 3. Gemini hero image service (new `backend/app/image_service.py`)
- `GEMINI_API_KEY` in `.env` (you said you have one — add it). Calls Gemini image model REST API with a prompt derived from topic title + key facts; saves PNG to `backend/generated_images/<concept_id>.png`, served via FastAPI `StaticFiles` mount; cached per concept.
- `metadata["hero_image_url"]` set at session start. Any failure/no key → `null`; frontend falls back to a CSS gradient hero. 20s timeout so start never hangs.

### 4. Minor
- `requirements.txt` += `httpx`; update the two "do not add extra fields" prompt lines.

---

## Frontend — full rewrite of `src/` (delete the 2,534-line monolith)

**New structure:** `src/api.js` (fetch wrapper, `VITE_API_BASE` env), `src/theme.css` (design system), `src/data/` (topic cards, quizzes-agnostic), `src/components/` (TopBar, XPBar, ScoreRing, Mascot, ConfettiBurst, ChoiceButton), `src/screens/` (Auth, Home, Intake, Forging, Lesson, Visualizer, Challenge, Feedback, Summary), `src/viz/` (ScenePlayer engine).

**New deps:** `framer-motion` (springy motion), `canvas-confetti`, `lucide-react` (clean icons).

**Flow & screens (light Duolingo-style: chunky rounded buttons with 3D press, green/blue/yellow palette, friendly mascot, big type, minimal text):**
1. **Auth** — restyled, quick.
2. **Home** — colorful topic cards (DSA gallery, per-problem art from emoji/gradient) + prominent "Learn Anything" input with example chips.
3. **Intake** — 3 MCQ warm-up questions, one at a time, progress dots, playful copy ("Not graded — just so I know where to start"). MCQ options as tappable cards, not a textarea.
4. **Forging** — animated pipeline (Detector → Architect → Professor → Animator icons lighting up with live stage status) while the frontend silently chains `advance` ×4 (diagnose→plan→explain→visualize), pre-generating everything. One loading screen replaces three text screens.
5. **Lesson** — explanation restructured into 3 short visual chapters (Intuition → Mechanism → Application): hero image (Gemini) or gradient, key facts as tappable flip-chips, mini inline visuals; ~60% less text than today.
6. **Visualizer (the showpiece)** — `ScenePlayer`: full CSS/emoji actor scene, play/pause/speed, timeline with step dots + captions, animated transitions between steps. **Predict moments**: scene pauses and asks "what happens next?" with MCQ built from the spec's checkpoint questions. DSA keeps **side-by-side naive vs optimized synced scenes** (the existing USP), non-CS topics get a single story scene. No code editor, no complexity jargon panel — complexity revealed as a fun "cost meter" comparison.
7. **Challenge** — the frozen scene + one prediction question (MCQ) + a short "explain why" box (reasoning still graded by the evaluation agent, unchanged).
8. **Feedback** — animated score ring, mastery meter moves, misconceptions shown as "🚫 Myth busted" cards, adaptation as a friendly next-step card (rewatch key moment ⇄ or quest complete).
9. **Summary** — mastery ring, XP, accuracy, myth-bust list, hero image, confetti, replay/back-to-topics. XP + streak bits persist via localStorage.

---

## Verification
1. Restart backend + frontend; run `verify_session_flow.py` (backend regression) — must stay green.
2. Browser-walk the full flow for **two-sum** (dual scenes + predictions) and **photosynthesis** (custom scene + hero image) — the exact path from your screenshots.
3. Test no-key fallbacks (scene fallback builder, gradient hero).

Servers are still running from earlier (backend :8000, frontend :5173) — I'll restart them as I go.