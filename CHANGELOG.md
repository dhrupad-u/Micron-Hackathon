# Changelog — Adaptive Learning Platform (Hackathon Submission)

Below is a detailed timeline of all modifications, iterations, and features added to build the Adaptive Learning Platform for DSA (Arrays & Strings: Two Sum).

## [1.1.0] - 2026-08-28

### Added
- **Problem Statement Screen**: Created a static screen detailing the Two Sum challenge (problem description, examples, constraints) showing immediately after subtopic selection, resolving the missing context before initial assessment.
- **Beginner Diagnose Route**: Added an "I don't know how to solve this — just teach me" link that feeds the diagnostic agent a low-confidence test string (`"I don't really know anything about this."`) to smoothly auto-generate a suitable entry-level plan.
- **Real Evaluation Agent**: Structured LLM implementation evaluating factual correctness against `ConceptModel.key_facts` and checking for student reasoning quality and misconception persistence.
- **Real Adaptation Agent**: Structured LLM implementation deciding instructional pivots (`continue`, `simplify`, `re-teach`, `hint`, `flag_misconception`) and routing student states dynamically.
- **Visualizer Checkpoint Pagination**: Added interactive `← Prev Q` and `Next Q →` question page-turner buttons to handle cases where multiple checkpoint questions are returned by the backend spec.
- **Session Progress Buttons**: Added a "Proceed to Practice" button to transition from visualization to practice, and custom action buttons dynamically mapped to adaptation decisions (e.g. "Try Again" or "Review Comparison Visualizer").
- **Closed-Loop Practice UI & Completed Screen**: Added custom visual screens for the Practice, Evaluate, Adapt, and Completed stages to replace raw JSON display placeholders.

### Changed
- **Autoplay Question Blocking Removed**: Moved the checkpoint questions block to render only at the final `conclusion` step of the visualizer, allowing autoplay to run smoothly without pausing mid-animation.
- **API Routing & LLM Config**: Corrected `.env` variable mapping so `XAI_API_KEY` routes properly to Groq/xAI endpoints, and fixed UUID key parsing that forced fallback OpenAI routing.

---

## Key Design Decisions & Iterations
1. **Autoplay Block Resolution**: Initially, the visualizer was designed to pause mid-animation for checkpoint questions. In practice, this broke autoplay under time pressure. The checkpoint questions were moved to the final state (`conclusion`) of the timeline to provide a seamless visualization flow, leaving the questions as a final checkpoint.
2. **Auto-Advance on Evaluate Stage**: To optimize UX and remove dummy transition button clicks, the frontend now detects when the session status is `'evaluate'` and automatically sends the advance request to run Adaptation.
3. **Structured Fallbacks**: If the LLM grading or adaptation output fails to parse, the system safely falls back to a conservative default (grading failed, mark for review) to prevent frontend crashes.
