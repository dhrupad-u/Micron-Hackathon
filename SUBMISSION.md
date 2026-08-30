# DeepDive — An Adaptive Agentic CS Learning Engine

## The Problem

CS students preparing for technical interviews — especially while also job hunting — have a content problem that isn't actually a content problem. GeeksforGeeks, LeetCode, YouTube, and generic AI chatbots all provide explanations. What none of them do is find out *what a specific student actually misunderstands* before teaching, or verify afterward whether the student's answer reflects real understanding or just a plausible-sounding guess.

The result: a student can read an explanation, feel like they understood it, and still hold the exact misconception the explanation was supposed to fix — because nothing in the loop checked.

**Who has this problem:** CS students and new-grad candidates preparing for technical interviews, who need to turn passive studying into real, checkable understanding, often under time pressure while also managing a job search.

**The bottleneck:** self-diagnosis. Students don't reliably know what they don't know, and static content has no way to find out.

---

## What DeepDive Does

DeepDive is an agentic learning engine, not a static tutor. Before teaching a concept, it diagnoses what the student already understands and what misconceptions they may hold. It then teaches through an interactive, CSS-animated visualization — with multiple solution approaches available side by side (e.g. brute force vs. hash map for Two Sum), each with its own explanation, animation, and editable code. After the student answers a checkpoint question, an Evaluation Agent grades the *reasoning*, not just the surface answer, against the concept's ground-truth facts — and an Adaptation Agent decides what happens next: continue, simplify, re-teach with a different representation, or explicitly flag and correct a detected misconception before letting the student retry.

The core engine is domain-generic by design. This build implements one domain — Computer Science, with sub-domains Software Engineering, Data, AI/ML, Security, and Infrastructure — fully wired for one concept (Two Sum, under DSA/Arrays), with the rest of the topic catalog present in the UI as "coming soon" placeholders to demonstrate the intended scope without overclaiming what's actually built.

---

## Architecture

```text
Student Interaction Layer (sign-up/sign-in → topic → subtopic → problem)
    │
    ▼
Orchestrator (deterministic state machine)
    │
    ├─ Learner Diagnostic Agent   → DiagnosticReport
    ├─ Learning Planner Agent     → LearningPlan (stub)
    ├─ Concept Agent              → ConceptModel (methods: brute force, hash map)
    ├─ Visualization Agent        → VisualizationSpec (per method)
    ├─ Practice Agent             → ExerciseSet (stub)
    ├─ Evaluation Agent           → EvaluationResult
    ├─ Adaptation Agent           → AdaptationDecision
    │
    ▼
Deterministic CSS Renderer (array / comparison / highlight / transition primitives)
    │
    ▼
Learning State Store (StudentSession)
```

Eight agents were designed; five (Diagnostic, Concept, Visualization, Evaluation, Adaptation) are fully implemented with real LLM calls and fallback-to-stub on failure. Planner and Practice remain deterministic stubs — a scope decision made explicitly to keep the hackathon build small and demonstrable rather than broad and unfinished, per the brief's own guidance that "purposeful choices matter more than the number of components."

**Why each agent is genuinely agentic, not just an LLM call wrapped in a function:**
- *Diagnostic Agent* reasons over free-text student input against a defined misconception list — it doesn't just classify, it decides confidence and which prerequisites are likely known.
- *Concept Agent* generates a canonical explanation *conditioned on* the diagnostic output — the same concept is explained differently depending on what was detected.
- *Visualization Agent* chooses and populates a structured spec rather than generating raw HTML/CSS directly — reasoning is separated from rendering by design (see Visualization Contract below).
- *Evaluation Agent* judges reasoning quality against ground-truth facts, not surface correctness.
- *Adaptation Agent* makes a real routing decision (continue / simplify / re-teach / hint / flag_misconception) that changes what the student sees next — this is where the loop actually closes.

---

## Domain Model

The core engine (orchestrator, state model, evaluation, adaptation, rendering) is domain-agnostic. A `DomainAdapter` provides a `ConceptNode` (canonical definition, prerequisites, misconceptions) per topic. Adding a new CS sub-domain — or in the future, a non-CS domain like Biology — means writing a new adapter, not touching the core engine.

Implemented: one `ConceptNode` — **Two Sum (Array/DSA)** — with two methods (brute force, hash map), each with its own explanation, `VisualizationSpec`, and code sample.

Present in the UI, not yet implemented: Data, AI/ML, Security, Infrastructure sub-domains, and additional DSA subtopics (Stacks, Trees, etc.) — shown as disabled tiles to demonstrate the intended catalog structure honestly, without claiming functionality that doesn't exist.

---

## Visualization Contract

Agents never generate raw HTML/CSS. Instead, the Visualization Agent emits a structured JSON spec (`type`, `entities`, `relations`, `states`, `transitions`, `questions`) built from a small set of reusable primitives — `flow`, `array`, `comparison`, `node`, `edge`, `highlight`, `transition`, `question`, `metric`. A deterministic frontend renderer turns this into CSS-animated, step-through UI (step counter, play/pause/next/previous). This separation is what makes the "generic across domains" claim credible — the same primitives that animate an array scan could animate a different domain's process without new rendering code.

---

## Authentication

Lightweight, demo-scoped: username/password with salted hashing, an in-memory/lightweight session token, and per-user session ownership enforced on the backend (mismatched user → 403). This is intentionally not production-grade (no OAuth, no password reset, no email verification) — a deliberate scope decision given the 48-hour window, not an oversight.

---

## Improvement Changelog

| Stage | What we tried and why | Evidence | Decision / Learning |
|---|---|---|---|
| Baseline | Single direct LLM call: "Explain Two Sum and give me a solution," no diagnosis, no structure. | Static, generic explanation regardless of what the student already knew or misunderstood. | Established the starting point — proved that a single prompt can't detect or correct a specific misconception. |
| Iteration 1 | Built the orchestrator + 8-agent architecture as stubs (fake but correctly-shaped output), no LLM calls yet. | Full session loop (diagnose → plan → explain → visualize → practice → evaluate → adapt → completed) verified end to end via `verify_session_flow.py`. | Kept — proved the state machine and routing logic before spending any LLM budget on reasoning quality. |
| Iteration 2 | Wired real LLM calls into Diagnostic + Concept agents only, grounded against the domain adapter's canonical facts/misconception list. | Tested 3 student inputs: correctly detected the "HashMap sorts data" misconception (confidence 0.86) and correctly reported low confidence with no false positives on a complete-beginner input (confidence 0.2). | Kept — confirmed the diagnostic step genuinely changes downstream behavior rather than being decorative. |
| Iteration 3 | Built the Visualization Agent + CSS renderer for the array/comparison primitives; initially paused mid-animation for "predict before reveal" checkpoint questions. | Mid-animation pausing broke autoplay under testing — the animation stalled at step 1 whenever a question was unanswered. | Removed — checkpoint questions moved to the final state only. Logged here rather than silently dropped, since it's a real reduction in the original interactivity design, made under time pressure. |
| Iteration 4 | Added multi-method support (brute force + hash map) as a first-class list on `ConceptModel`, each with its own live-generated explanation, code, and visualization spec, plus a method-switcher UI. | Verified both methods render, step through, and swap code/explanation/visualization in sync. | Kept — this is what makes the engine demonstrate "purposeful" agent design rather than a single hardcoded path. |
| Iteration 5 | Wired real Evaluation + Adaptation agents; ran 4 test cases (correct, "HashMap sorts data," vague/uncertain, and a subtler "hashes the target sum" misconception). | All 4 cases produced correctly differentiated evaluations and adaptation actions (continue / flag_misconception+retry / re-teach / flag_misconception+retry), each with a rationale grounded in the concept's actual facts. | Kept — this is the loop-closing step; without it, "adaptive" was only a claim, not a behavior. |
| Final | Ran a baseline comparison (single direct LLM grading call, no context) against the pipeline on the misconception cases. | Grading scores were similar between baseline and pipeline — the baseline is not naive. The real difference: only the pipeline takes a curriculum action (routes to retry, adjusts difficulty, gives a rationale grounded in the concept graph); the baseline outputs static text and the student stays stuck. | Main contribution identified: **the Action Gap** — not "we grade better," but "we're the only one that does something about it." |

---

## Measured Improvement — The Action Gap

| Feature | Grounded Multi-Agent Pipeline | Baseline Direct LLM Call |
|---|---|---|
| Grading accuracy on misconception cases | Comparable to baseline | Comparable to pipeline |
| Closes the loop | Yes — triggers `flag_misconception`, routes to retry, adjusts difficulty | No — outputs text only, state doesn't change |
| Tutoring specificity | Rationale grounded in the concept's canonical facts and the specific misconception detected | Generic, textbook-style feedback |
| What the student experiences next | A targeted re-teach via the visualization player | Nothing — stays in the same state |

This is an honest reframe from an earlier hypothesis in this build. We initially expected the baseline to also fail at *detecting* misconceptions; it didn't, consistently. The real, demonstrable gap is what happens after detection.

---

## Hot Take

Grading accuracy is not the bottleneck in AI tutoring — modern LLMs are already reasonably good at spotting a wrong answer, even without special scaffolding. The bottleneck is that detecting a misconception and doing something structured about it are two different capabilities, and most "AI tutor" demos only build the first one. An agentic architecture earns its complexity in the second half of the loop, not the first — which is a useful thing to know before deciding where to spend the 48 hours next time.

---

## Multi-Problem Scaling & Dynamic Loop Closure

We scaled the Domain Adapter from the original single *Two Sum* problem to **6 fully interactive problems** in the Arrays/DSA subtopic, enabling Contains Duplicate, Valid Anagram, Best Time to Buy and Sell Stock, Maximum Subarray, and Valid Parentheses as real, clickable entries in the frontend challenges list.

By verifying the new additions using our automated test script (`run_five_problems_eval.py`), we confirmed that the pipeline generalizes **out of the box** without any special-casing:
1. **Contains Duplicate**: Concept Agent generated brute-force, sorting, and hash-set methods. Evaluator correctly flagged the sorting misconception (`sorting is the only way to solve this`) and routed the candidate back to visualize.
2. **Valid Anagram**: Correctly generated frequency counting and sorting methods, and flagged the character set presence misconception.
3. **Best Time to Buy/Sell Stock**: Correctly generated single-pass min-tracking, and caught the buy-lowest-regardless-of-order misconception, triggering a `simplify` curriculum action.
4. **Maximum Subarray (Kadane)**: Generated Kadane's greedy single-pass, and flagged the negative running sum reset misconception.
5. **Valid Parentheses**: Genuinely matched stack dynamics. The Visualization Agent **successfully generated stack-specific LIFO spec** (`stackStructure` entity kind) instead of an array layout. Caught the naive bracket count misconception and routed to `visualize` retry state with difficulty `easy`.

**Known limitations, stated directly:** This build proves the multi-agent loop on 6 standard DSA concepts in the Arrays/Strings sub-domain. While the visualization primitives (such as arrays, comparisons, and stacks) are generic, expanding to non-linear graphs or non-CS domains would require implementing new UI rendering shapes. Evaluation was tested against a hand-picked set of misconception inputs rather than a large blind student population.
