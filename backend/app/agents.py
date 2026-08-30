from __future__ import annotations

import json
import logging
from typing import Any

from .domain import get_concept_node, get_topic_brief
from .llm_client import call_structured_llm
from .schemas import (
    AdaptationDecision,
    ChatAskRequest,
    ChatAskResponse,
    ConceptModel,
    DiagnosticReport,
    EvaluationResult,
    ExerciseSet,
    ExerciseTask,
    LearningPlan,
    MethodModel,
    QuizQuestion,
    SceneActor,
    SceneEffect,
    SceneScript,
    SceneStep,
    StudentSession,
    TopicBlueprint,
    VisualizationEntity,
    VisualizationQuestion,
    VisualizationRelation,
    VisualizationSpec,
    VisualizationState,
    VisualizationTransition,
)


LOGGER = logging.getLogger(__name__)


def log_agent_call(session: StudentSession, agent_name: str, payload: dict[str, Any]) -> None:
    trace = session.metadata.setdefault("agent_trace", [])
    trace.append({"agent": agent_name, "payload": payload})


# ── Topic Synthesis Agent: builds a curriculum node for ANY free-text topic ──

def _topic_synthesis_fallback(topic_request: str) -> TopicBlueprint:
    """Deterministic blueprint built from the raw topic text (no LLM needed)."""
    topic = (topic_request or "").strip() or "A new topic"
    slug = "custom-" + "".join(
        ch if ch.isalnum() else "-" for ch in topic.lower()
    ).strip("-")[:40]
    title = topic if len(topic) <= 80 else topic[:77] + "..."
    return TopicBlueprint(
        concept_id=slug,
        title=title,
        domain="Custom",
        subdomain="Learner Requested",
        canonical_definition=(
            f"{title} is a core domain concept that connects starting conditions to observable outcomes "
            f"through a structured, step-by-step mechanism."
        ),
        key_facts=[
            f"{title} operates through a specific transformation sequence rather than random events.",
            f"Key variables in {title} adjust dynamically in response to system changes.",
            f"Understanding {title} allows predicting outcomes in real-world scenarios.",
        ],
        prerequisites=["basic background knowledge", "curiosity about how systems work"],
        misconceptions=[
            f"Knowing the name of {title} means you understand its underlying mechanism",
            f"The steps in {title} happen independently without affecting each other",
            f"{title} is static and never adapts to changing external factors",
        ],
        explanation_depths=[
            f"{title} intuition: core relationship between inputs and outputs",
            f"{title} mechanism: step-by-step operational flow",
            f"{title} application: real-world impact and constraints",
        ],
        narrative_intuition=(
            f"Imagine you are observing {title} in action for the first time. "
            f"At its heart, {title} is about how inputs are transformed into expected outputs. "
            f"Instead of viewing it as abstract theory, think of it as a set of rules where every action triggers a direct, logical reaction."
        ),
        deep_mechanism=(
            f"The mechanism of {title} unfolds in distinct phases:\n"
            f"1. Setup & Baseline: Initial state is established with starting parameters.\n"
            f"2. Trigger & Interaction: Elements interact according to core domain rules.\n"
            f"3. Transformation: Intermediate state resolves into the final observable outcome."
        ),
        real_world_scenario=(
            f"In real life, {title} can be seen whenever systems need to balance competing forces or process inputs efficiently. "
            f"For instance, when conditions shift suddenly, {title} governs how stability is restored."
        ),
        common_pitfalls=[
            f"Confusing correlation with causation when observing {title}.",
            f"Assuming all steps in {title} have equal weight regardless of initial conditions.",
        ],
        input_display=f"{title}: input → mechanism → output",
        example_values=["start", "process", "result"],
        example_walkthrough=f"Step 1: Identify starting values. Step 2: Apply transformation rules. Step 3: Verify the outcome.",
        practice_challenge=f"In your own words, explain how {title} works and describe a real situation where you would observe it.",
        diagnostic_quiz=[
            QuizQuestion(
                question=f"What is the single most important idea behind {title}?",
                options=[
                    f"Inputs follow a logical rule to produce outputs",
                    f"It only happens by random chance",
                    f"It only applies to theoretical computer algorithms",
                    f"It cannot be measured or observed",
                ],
                correct_index=0,
                misconception_tag="randomness assumption",
                explanation=f"{title} is governed by a deterministic, observable mechanism.",
            ),
            QuizQuestion(
                question=f"When studying {title}, why is it crucial to look at step-by-step examples?",
                options=[
                    "Because memorizing names isn't enough to predict how it behaves",
                    "Because step-by-step examples are only for beginners",
                    "Because the order of steps never matters",
                    "Because examples change the underlying definition",
                ],
                correct_index=0,
                misconception_tag="superficial memorization",
                explanation="Real understanding comes from tracing the step-by-step state changes.",
            ),
            QuizQuestion(
                question=f"How would you explain {title} to someone who has never heard of it?",
                options=[
                    f"Focus on the main real-world analogy and how inputs become outputs",
                    f"List 50 technical terms without context",
                    f"Tell them it is too complex to understand",
                    f"Skip the mechanism and only give a single formula",
                ],
                correct_index=0,
                misconception_tag="overcomplication",
                explanation="The best explanations build clear intuition using analogies before technical details.",
            ),
        ],
    )


def topic_synthesis_agent(topic_request: str, student_level: str = "beginner") -> TopicBlueprint:
    """Synthesize a full curriculum blueprint for an arbitrary learner-requested topic."""
    system_prompt = (
        "You are a master educator and curriculum-synthesis agent for an adaptive learning platform. "
        "A learner wants to learn ANY topic they typed — it may be computer science, physics, economics, "
        "biology, history, music theory, a software tool, or anything else.\n"
        "Design a rich, engaging micro-lesson blueprint for that topic.\n\n"
        "REQUIREMENTS FOR CONCEPTUAL DEPTH:\n"
        "  1. concept_id: short kebab-case slug prefixed with 'custom-'.\n"
        "  2. title: clean human-readable lesson title (max ~80 chars).\n"
        "  3. canonical_definition: 2-4 clear sentences defining the topic precisely.\n"
        "  4. key_facts: 3-5 ground-truth statements explaining core principles.\n"
        "  5. narrative_intuition: 2-3 detailed paragraphs building a vivid, clear analogy/story "
        "that makes the concept instantly intuitive for a first-time learner. Write rich prose!\n"
        "  6. deep_mechanism: 2-3 detailed paragraphs explaining EXACTLY how it works step-by-step, "
        "the underlying rules, state changes, and mechanics. Write deep, engaging educational prose!\n"
        "  7. real_world_scenario: 1-2 paragraphs giving a concrete, real-life case study or example "
        "showing where and why this concept matters in practice.\n"
        "  8. common_pitfalls: 2-3 common misconceptions or traps explained with clear explanations of why they occur.\n"
        "  9. input_display: ONE short line (max ~60 chars) showing the visualizer input state.\n"
        "  10. example_values: 3-6 short single-word/token strings representing states for the visualizer.\n"
        "  11. example_walkthrough: a concrete worked example with step-by-step numbers/labels.\n"
        "  12. practice_challenge: ONE open-ended prompt asking the student to explain the mechanism in their own words.\n"
        "  13. diagnostic_quiz: EXACTLY 3 highly valid, topic-specific multiple-choice warm-up questions. "
        "Each question must test real domain intuitions for THIS specific topic (e.g. for Supply & Demand, test price adjustments when supply drops; for WiFi, test radio wave transmission). "
        "Provide 4 plausible options, correct_index (0-3), misconception_tag, and a 1-sentence explanation."
    )
    user_prompt = json.dumps({
        "topic_request": topic_request,
        "student_level": student_level,
        "output_type": "TopicBlueprint",
    })
    return call_structured_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_model=TopicBlueprint,
        fallback=lambda: _topic_synthesis_fallback(topic_request),
    )


def chat_assistant_agent(
    session: StudentSession,
    user_question: str,
    current_screen: str = "general",
) -> ChatAskResponse:
    """Fast 1-2 sentence AI assistant (DeepBot) answering learner questions on any screen."""
    concept = session.concept_history[0] if session.concept_history else None
    brief = get_topic_brief(session.metadata.get("concept_id", ""))
    topic = session.active_topic

    title = concept.title if concept else (brief.title if brief else topic)
    definition = concept.canonical_definition if concept else (brief.canonical_definition if brief else "")
    facts = concept.key_facts if concept else (brief.key_facts if brief else [])

    system_prompt = (
        "You are DeepBot, a friendly, ultra-clear AI learning companion owl. "
        f"The student is on the '{current_screen}' screen studying '{title}'.\n"
        f"Context definition: {definition}\n"
        f"Key facts: {'; '.join(facts[:3])}\n\n"
        "Your task: Answer the student's question in EXACTLY 1 to 2 short, crisp, encouraging sentences. "
        "Be extremely clear and educational. Do not use buzzwords or long bullet lists. "
        "Also provide 2 short (3-5 word) suggested follow-up question chips in 'suggested_followups'."
    )
    user_prompt = json.dumps({
        "user_question": user_question,
        "screen": current_screen,
        "output_type": "ChatAskResponse",
    })

    def _fallback() -> ChatAskResponse:
        return ChatAskResponse(
            reply=f"Great question! In {title}, the core idea is to focus on how the mechanism transforms the input step by step.",
            suggested_followups=["Explain simpler", "Give an example"],
        )

    try:
        return call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ChatAskResponse,
            fallback=_fallback,
        )
    except Exception:
        return _fallback()



def _diagnostic_fallback(session: StudentSession) -> DiagnosticReport:
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    node = get_concept_node(concept_id)
    return DiagnosticReport(
        understanding=["basic programming"],
        missing_prerequisites=node.prerequisites,
        misconceptions=[],
        confidence=0.5,
        summary=f"No prior diagnosis available for {node.title}."
    )


def _concept_fallback(session: StudentSession) -> ConceptModel:
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    node = get_concept_node(concept_id)
    brief = get_topic_brief(concept_id)

    # Use real key_facts from blueprint if available, otherwise node explanation depths
    if brief and brief.key_facts:
        key_facts = brief.key_facts
    elif node.explanation_depths:
        key_facts = node.explanation_depths
    else:
        key_facts = [f"{node.title} has a core mechanism that drives its behavior"]

    # For DSA concepts use algorithm-style methods; for custom topics use generic approaches
    is_dsa = node.domain in ("CS",) and concept_id != concept_id.startswith("custom-")
    if brief:  # custom synthesized topic
        approach_name = brief.title
        step1 = brief.example_walkthrough.split(".")[0] if brief.example_walkthrough else f"Initial approach to {brief.title}"
        fallback_methods = [
            MethodModel(
                id="naive-approach",
                name=f"Basic Approach",
                explanation=f"The straightforward way to understand {brief.title}: {brief.explanation_depths[0] if brief.explanation_depths else step1}.",
                complexity={"time": "n/a", "space": "n/a"},
                code=f"# Basic approach\n# {brief.example_walkthrough[:100] if brief.example_walkthrough else 'Step through the process manually'}",
                visualization_spec_ref="naive-visual"
            ),
            MethodModel(
                id="optimized-approach",
                name=f"Deeper Understanding",
                explanation=f"A deeper view of {brief.title}: {brief.explanation_depths[-1] if len(brief.explanation_depths) > 1 else brief.canonical_definition}.",
                complexity={"time": "n/a", "space": "n/a"},
                code=f"# Optimized approach\n# {brief.canonical_definition[:100]}",
                visualization_spec_ref="optimized-visual"
            )
        ]
    else:
        fallback_methods = [
            MethodModel(
                id="brute-force",
                name="Naive / Brute Force Approach",
                explanation=f"A naive O(N\u00b2) comparison approach to solve {node.title}.",
                complexity={"time": "O(N\u00b2)", "space": "O(1)"},
                code="# Naive approach implementation\nfor i in range(len(nums)):\n    for j in range(i+1, len(nums)):\n        pass",
                visualization_spec_ref="bf-visual"
            ),
            MethodModel(
                id="optimized",
                name="Optimized Approach",
                explanation=f"An efficient O(N) optimized approach to solve {node.title}.",
                complexity={"time": "O(N)", "space": "O(N)"},
                code="# Optimized approach implementation\nseen = {}\nfor i, val in enumerate(nums):\n    pass",
                visualization_spec_ref="optimized-visual"
            )
        ]

    return ConceptModel(
        concept_id=node.concept_id,
        title=node.title,
        canonical_definition=node.canonical_definition,
        key_facts=key_facts,
        prerequisites=node.prerequisites,
        misconceptions=node.misconceptions,
        explanation_summary=node.canonical_definition,
        teaching_emphasis=[node.title],
        methods=fallback_methods,
        narrative_intuition=(
            brief.narrative_intuition if brief and brief.narrative_intuition else
            f"Think of {node.title} as a fundamental mechanism connecting inputs to outcomes. "
            f"Instead of memorizing definitions, imagine walking through a real example step by step to see how each action triggers a logical reaction."
        ),
        deep_mechanism=(
            brief.deep_mechanism if brief and brief.deep_mechanism else
            f"The underlying mechanism of {node.title} operates in clear stages:\n"
            f"1. Setup: Starting parameters and input data are loaded.\n"
            f"2. Processing: Core rules and transformations are applied sequentially.\n"
            f"3. Resolution: The final state is computed and verified."
        ),
        real_world_scenario=(
            brief.real_world_scenario if brief and brief.real_world_scenario else
            f"In practical applications, {node.title} is utilized wherever efficient processing and predictable outcomes are essential."
        ),
        common_pitfalls=(
            brief.common_pitfalls if brief and brief.common_pitfalls else node.misconceptions
        ),
    )


def _guard_against_ground_truth(model: ConceptModel, node) -> ConceptModel:
    if node.concept_id != "two-sum-hashmap":
        return model
    ground_truth_keywords = [
        "brute force",
        "hash map",
        "target - current_value",
        "average lookup",
        "O(n) average time",
    ]
    joined = " ".join(model.key_facts).lower()
    if not all(keyword in joined for keyword in ["brute force", "hash map", "target - current_value"]) and model.concept_id == node.concept_id:
        LOGGER.warning("LLM concept facts conflict with adapter ground truth; using domain adapter truth instead.")
        model.key_facts = [
            "Brute force checks every pair of numbers",
            "A hash map stores values already seen",
            "For each value, the relevant check is target - current_value",
            "Average lookup in a hash map is O(1), so the algorithm becomes O(n) average time"
        ]
        model.canonical_definition = node.canonical_definition
        model.prerequisites = node.prerequisites
        model.misconceptions = node.misconceptions
    return model


def diagnostic_agent_real(session: StudentSession) -> DiagnosticReport:
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    node = get_concept_node(concept_id)
            
    student_text = (session.student_profile.self_description or "").strip() or session.student_profile.current_level
    system_prompt = (
        "You are a careful student-diagnostic agent for an adaptive learning system. "
        "Ground your reasoning only in the given concept prerequisites and misconceptions list. "
        "Do not invent new misconceptions. Be conservative: if evidence is weak, say low confidence and no clear misconception."
    )
    user_prompt = json.dumps({
        "student_text": student_text,
        "concept_title": node.title,
        "prerequisites": node.prerequisites,
        "misconceptions": node.misconceptions,
        "output_type": "DiagnosticReport",
    })
    try:
        model = call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=DiagnosticReport,
            fallback=lambda: _diagnostic_fallback(session),
        )
        log_agent_call(session, "DiagnosticAgent", {"student_profile": session.student_profile.model_dump(), "llm_output": model.model_dump()})
        return model
    except Exception:
        fallback = _diagnostic_fallback(session)
        log_agent_call(session, "DiagnosticAgent", {"student_profile": session.student_profile.model_dump(), "fallback_used": True})
        return fallback


def concept_agent_real(session: StudentSession) -> ConceptModel:
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    node = get_concept_node(concept_id)
    brief = get_topic_brief(concept_id)

    diagnosis = session.diagnosis or DiagnosticReport(
        understanding=[],
        missing_prerequisites=node.prerequisites,
        misconceptions=[],
        confidence=0.5,
        summary="No prior diagnosis available."
    )

    is_custom = bool(brief)  # synthesized topic vs curated DSA
    if is_custom:
        method_instruction = (
            "You must generate exactly 2 methods in the 'methods' field. "
            f"This is a '{node.domain}' topic (not necessarily computer science), so the approaches should be "
            "conceptually meaningful ways to understand or apply this topic — NOT generic CS algorithm patterns. "
            "Example: for 'Supply and Demand', methods could be 'Graphical Analysis' vs 'Mathematical Equilibrium'. "
            "For 'Photosynthesis' they could be 'Light Reactions' vs 'Calvin Cycle'. "
            "Use id values like 'approach-1' and 'approach-2'. "
            "Set complexity.time and complexity.space to 'n/a' for non-computational topics. "
            "The 'code' field should contain a structured outline, pseudocode, or key formula — not Python unless the topic is programming."
        )
    else:
        method_instruction = (
            "You must generate a list of 2-3 different algorithmic approaches in the 'methods' field. "
            f"For {node.title}, include an initial/naive approach (id should contain 'brute' or 'naive') and "
            "one or two better approaches. Each must have proper time/space complexity."
        )

    brief_context = ""
    if brief:
        brief_context = (
            f"\n\nThe learner requested this topic. Here is the pre-synthesized blueprint with rich educational content:\n"
            f"narrative_intuition (copy this or improve it): {brief.narrative_intuition}\n"
            f"deep_mechanism (copy this or improve it): {brief.deep_mechanism}\n"
            f"real_world_scenario (copy this or improve it): {brief.real_world_scenario}\n"
            f"common_pitfalls: {brief.common_pitfalls}\n"
            f"key_facts: {brief.key_facts}\n"
            "You MUST populate the narrative_intuition, deep_mechanism, real_world_scenario, and common_pitfalls "
            "fields in your ConceptModel output. Do NOT leave them empty strings."
        )

    system_prompt = (
        "You are a master concept-explainer agent for an adaptive learning platform. "
        "Use the provided ground-truth concept node as the source of truth. "
        "Write in plain, engaging language tailored to the student's current skill level.\n\n"
        "CRITICAL — you MUST populate ALL of these fields with rich, detailed content:\n"
        "  narrative_intuition: 2-3 paragraphs building vivid, clear intuition with analogy or story. "
        "Write as if explaining to a curious 18-year-old for the first time. Be specific and concrete.\n"
        "  deep_mechanism: 2-3 paragraphs explaining EXACTLY how it works step-by-step with real examples "
        "and numbers. Name the specific rules, transformations, and state changes.\n"
        "  real_world_scenario: 1-2 paragraphs with a concrete real-world case study showing why this matters.\n"
        "  common_pitfalls: 2-3 misconceptions students commonly hold, with clear explanations.\n"
        "  key_facts: 3-5 specific verifiable facts — NOT generic placeholders.\n"
        "  explanation_summary: 2-3 sentence clear summary.\n\n"
        + method_instruction
        + "\nEach method must have: id, name, explanation, complexity dict (keys: 'time', 'space'), "
        "and a 'code' field with a clear pseudocode or outline."
        + brief_context
    )
    user_prompt = json.dumps({
        "concept": node.model_dump(),
        "diagnostic_report": diagnosis.model_dump(),
        "output_type": "ConceptModel",
        "topic": session.active_topic,
    })
    try:
        model = call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ConceptModel,
            fallback=lambda: _concept_fallback(session),
        )
        # Guarantee narrative fields are populated — fall back to blueprint if LLM left them empty
        if brief:
            if not model.narrative_intuition and brief.narrative_intuition:
                model.narrative_intuition = brief.narrative_intuition
            if not model.deep_mechanism and brief.deep_mechanism:
                model.deep_mechanism = brief.deep_mechanism
            if not model.real_world_scenario and brief.real_world_scenario:
                model.real_world_scenario = brief.real_world_scenario
            if not model.common_pitfalls and brief.common_pitfalls:
                model.common_pitfalls = brief.common_pitfalls
        model = _guard_against_ground_truth(model, node)
        log_agent_call(session, "ConceptAgent", {"target": session.active_topic, "llm_output": model.model_dump()})
        return model
    except Exception:
        fallback = _concept_fallback(session)
        log_agent_call(session, "ConceptAgent", {"target": session.active_topic, "fallback_used": True})
        return fallback


def diagnostic_agent_stub(session: StudentSession) -> DiagnosticReport:
    log_agent_call(session, "DiagnosticAgent", {"student_profile": session.student_profile.model_dump()})
    return _diagnostic_fallback(session)


def planner_agent_real(session: StudentSession) -> LearningPlan:
    """LLM-powered planner that tailors the learning sequence to diagnosis + topic."""
    log_agent_call(session, "PlannerAgent", {"active_topic": session.active_topic})
    topic = session.active_topic
    brief = get_topic_brief(session.metadata.get("concept_id", ""))
    concept_id = session.metadata.get("concept_id", "")
    node = get_concept_node(concept_id)
    diagnosis = session.diagnosis

    def _fallback() -> LearningPlan:
        prereq_step = (
            f"Address prerequisite: {brief.prerequisites[0]}"
            if brief and brief.prerequisites
            else "Identify the missing prerequisite knowledge"
        )
        return LearningPlan(
            goal=f"Explain how {topic} works and verify deep understanding, not just recognition",
            target_concept=topic,
            steps=[
                prereq_step,
                f"Walk through the initial/basic approach to {topic}",
                f"Compare with the best/optimized approach and explain why it is better",
                "Confirm understanding via prediction and reasoning"
            ],
            time_budget_minutes=20,
            rationale=f"Target the core mechanism of {topic} before discussing details."
        )

    system_prompt = (
        "You are a curriculum planner agent for an adaptive learning platform. "
        "Design a focused 20-minute lesson plan tailored to this student's diagnosed gaps. "
        "The topic can be ANY domain (CS, science, history, economics, etc). "
        "Output a LearningPlan JSON with: goal (1 sentence), target_concept, steps (3-5 action strings), "
        "time_budget_minutes (integer), and rationale (2-3 sentences explaining why this sequence). "
        "Make the steps specific to the actual topic — no generic placeholders."
    )
    user_prompt = json.dumps({
        "topic": topic,
        "prerequisites": (brief.prerequisites if brief else node.prerequisites),
        "misconceptions_to_address": (diagnosis.misconceptions if diagnosis else []),
        "student_level": (session.student_profile.current_level if session.student_profile else "beginner"),
        "output_type": "LearningPlan",
    })
    try:
        plan = call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=LearningPlan,
            fallback=_fallback,
        )
        return plan
    except Exception:
        return _fallback()


def planner_agent_stub(session: StudentSession) -> LearningPlan:
    """Alias kept for backward compatibility — now calls the real agent."""
    return planner_agent_real(session)


def concept_agent_stub(session: StudentSession) -> ConceptModel:
    log_agent_call(session, "ConceptAgent", {"target": session.active_topic})
    return _concept_fallback(session)


# ── Scene script helpers: generic animated scene used when the LLM omits/fails ──

_SCENE_ACTIONS = (
    "appear, disappear, move, pulse, shake, split, merge, fill, increment, "
    "highlight, dim, connect, emit"
)

_SCENE_KINDS = (
    "box, token, node, sun, drop, bubble, arrow, counter, chip, meter, lane, creature, stack"
)


def _scene_rules(step_range: str) -> str:
    return (
        "SCENE RULES — the required 'scene' field (this drives the animated visual the student watches):\n"
        "  CRITICAL — This is an EDUCATIONAL animation. Every step must teach something, not just move things around.\n"
        "  - scene.background: a one-word theme for the backdrop: 'sky', 'lab', 'grid', 'nature', 'space', or 'default'.\n"
        "  - scene.actors: 3 to 8 actors. Each actor represents a MEANINGFUL part of the concept — not a generic placeholder.\n"
        "    Actor fields: id (kebab-case), kind from " + _SCENE_KINDS + "; "
        "a SHORT label (max 12 chars) that names its ROLE in this specific concept; an emoji 'icon' relevant to the concept; "
        "x and y on a 0-100 percentage grid (y=10 is top, y=90 is bottom; keep x within 12-88, y within 15-85); "
        "optional 'value' (number) for counters/meters.\n"
        "  ACTOR DESIGN RULES:\n"
        "    * Name actors after their ROLE, not generic names. For Supply/Demand: name actors 'Buyer 💰', 'Seller 🏭', 'Price 📈'.\n"
        "    * For algorithmic problems: name actors after their data structure role ('Hash Map 🗂️', 'Current Num 🔍', 'Target ✅').\n"
        "    * Use 'box' kind for data/values, 'counter' for counts/quantities, 'meter' for progress/percentage, 'node' for concepts.\n"
        "  - scene.steps: " + step_range + ". STEP STRUCTURE:\n"
        "    * Step 0 (INTRO): Caption MUST state the problem: 'Problem: Given [input], find [goal].' Show all actors appearing.\n"
        "    * Middle steps: Each caption MUST say WHAT is changing AND WHY. E.g. 'Checking if 7 is in hash map — it IS, so we found our pair!'\n"
        "    * Final step (CONCLUSION): Caption MUST state the outcome: 'Answer: [specific result]. This took [O(n)] time.'\n"
        "    * Caption format: 'Step N: [specific action with real values from the example] → [what this reveals/proves]'.\n"
        "  - Each effect: 'actor' (an actor id), 'action' from " + _SCENE_ACTIONS + "; for 'move' set to_x/to_y (0-100);\n"
        "for 'split'/'merge'/'connect'/'emit' set 'target' to the partner actor id; 'label'/'value' update the actor's text/number.\n"
        "  - CRITICAL: The animation must tell a STORY about the concept. A student watching with no other context should understand:\n"
        "    1) What problem is being solved 2) The key mechanism/insight 3) The final answer or outcome.\n"
        "  - Use 'fill' effects with specific values from the example (e.g., fill a box with '9-2=7'), not generic 'step 1' text.\n"
    )


def _fallback_scene(session: StudentSession, naive: bool = False) -> SceneScript:
    """Deterministic scene: input row + scanner + counters, animated across the example values."""
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    brief = get_topic_brief(concept_id)
    if brief and brief.example_values:
        tokens = [str(t)[:10] for t in brief.example_values[:5]]
        bg = "nature"
    else:
        tokens = ["2", "7", "11", "15"]
        bg = "grid"

    n = len(tokens)
    x0 = max(14.0, 50 - (n - 1) * 9)
    actors = [
        SceneActor(id=f"box-{i}", kind="box", label=t, x=x0 + i * 18, y=30)
        for i, t in enumerate(tokens)
    ]
    actors.append(SceneActor(id="scanner", kind="arrow", label="scan", icon="👇", x=x0, y=50))
    if naive:
        actors.append(SceneActor(id="pairs", kind="counter", label="pairs tried", icon="🔁", value=0, x=50, y=76))
    else:
        actors.append(SceneActor(id="memory", kind="node", label="seen so far", icon="🧠", x=18, y=76))
        actors.append(SceneActor(id="result", kind="counter", label="progress", icon="✅", value=0, x=82, y=76))

    steps: list[SceneStep] = [
        SceneStep(
            id="s0",
            caption="Here comes the input." if not naive else "Watch the naive approach grind through the input.",
            effects=[SceneEffect(actor=f"box-{i}", action="appear") for i in range(n)]
            + [SceneEffect(actor="scanner", action="appear")],
        )
    ]
    for i, t in enumerate(tokens):
        effects = [SceneEffect(actor="scanner", action="move", to_x=x0 + i * 18, to_y=50)]
        if naive:
            effects.append(SceneEffect(actor="pairs", action="increment", value=i + 1))
            cap = f"Comparing {t} with every other value — work piles up."
        else:
            effects.append(SceneEffect(actor="memory", action="pulse", label=t))
            effects.append(SceneEffect(actor="result", action="increment", value=i + 1))
            cap = f"Handle {t} in one quick step and remember it."
        steps.append(SceneStep(id=f"s{i + 1}", caption=cap, effects=effects))
    steps.append(SceneStep(
        id=f"s{n + 1}",
        caption="Done — notice how much work each approach needed." if not naive else "Finally done. That was slow.",
        effects=[SceneEffect(actor="scanner", action="dim")],
    ))
    return SceneScript(background=bg, actors=actors, steps=steps)


def _visualization_fallback(session: StudentSession) -> VisualizationSpec:
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    node = get_concept_node(concept_id)

    # Determine type
    vis_type = "comparison"

    # Dynamic states based on concept prerequisites and title
    states = [
        VisualizationState(
            id="before",
            labels=[f"Start: {node.title} input is loaded."],
            highlight=["input"]
        ),
        VisualizationState(
            id="step-1",
            labels=[f"Stepping through optimized approach: scanning element/node."],
            highlight=["optimized"]
        ),
        VisualizationState(
            id="conclusion",
            labels=[f"Conclusion: Optimized approach resolved successfully."],
            highlight=["conclusion"]
        )
    ]

    return VisualizationSpec(
        type=vis_type,
        id=f"{concept_id}-visual",
        title=f"Visualization fallback — {node.title}",
        layout={"orientation": "left-right"},
        entities=[
            VisualizationEntity(id="input", kind="array", label="input values"),
            VisualizationEntity(id="optimized", kind="node", label="optimized process"),
            VisualizationEntity(id="conclusion", kind="node", label="result"),
        ],
        relations=[],
        states=states,
        transitions=[
            VisualizationTransition(**{"from": "before", "to": "step-1", "animation": "fade", "durationMs": 600}),
            VisualizationTransition(**{"from": "step-1", "to": "conclusion", "animation": "fade", "durationMs": 600}),
        ],
        questions=[
            VisualizationQuestion(
                id="q1",
                prompt=f"What is the time complexity of the optimized approach?",
                expectedObservations=["O(N)"]
            )
        ],
        expectedObservations=[],
        scene=_fallback_scene(session, naive=False),
    )


def _visualization_bf_fallback(session: StudentSession) -> VisualizationSpec:
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    node = get_concept_node(concept_id)

    vis_type = "comparison"

    states = [
        VisualizationState(
            id="before",
            labels=[f"Start: Naive approach input is loaded."],
            highlight=["input"]
        ),
        VisualizationState(
            id="bf-step",
            labels=[f"Stepping through naive approach sequentially."],
            highlight=["naive"]
        ),
        VisualizationState(
            id="conclusion",
            labels=[f"Conclusion: Naive approach has finished scanning."],
            highlight=["conclusion"]
        )
    ]

    return VisualizationSpec(
        type=vis_type,
        id=f"{concept_id}-bf-visual",
        title=f"Brute force visualization fallback — {node.title}",
        layout={"orientation": "left-right"},
        entities=[
            VisualizationEntity(id="input", kind="array", label="input values"),
            VisualizationEntity(id="naive", kind="node", label="naive process"),
            VisualizationEntity(id="conclusion", kind="node", label="result"),
        ],
        relations=[],
        states=states,
        transitions=[
            VisualizationTransition(**{"from": "before", "to": "bf-step", "animation": "fade", "durationMs": 600}),
            VisualizationTransition(**{"from": "bf-step", "to": "conclusion", "animation": "fade", "durationMs": 600}),
        ],
        questions=[
            VisualizationQuestion(
                id="q_bf_1",
                prompt=f"Why is the naive approach less efficient?",
                expectedObservations=["Nested scanning or extra work"]
            )
        ],
        expectedObservations=[],
        scene=_fallback_scene(session, naive=True),
    )


def _guard_visualization_spec(spec: VisualizationSpec, diagnosis) -> VisualizationSpec:
    """Ensure misconception-correcting labels are present when the diagnostic flagged them."""
    if diagnosis is None:
        return spec
    has_sort_misconception = "HashMap sorts data" in (diagnosis.misconceptions or [])
    if not has_sort_misconception:
        return spec

    correction = "The hash map does NOT sort data. Speed comes from O(1) average hash-based lookup, not ordering."
    # Check if any state label already mentions the correction
    all_labels = [lbl for st in spec.states for lbl in st.labels]
    already_corrected = any("sort" in lbl.lower() or "sorting" in lbl.lower() for lbl in all_labels)
    if already_corrected:
        return spec

    # Inject correction into the first state that highlights the hashmap entity
    for st in spec.states:
        if any("hash" in h.lower() or "map" in h.lower() for h in st.highlight):
            st.labels.insert(0, f"⚠ Misconception check: {correction}")
            break
    else:
        # fallback: inject into last state
        if spec.states:
            spec.states[-1].labels.insert(0, f"⚠ Misconception check: {correction}")
    return spec


def visualization_agent_real(session: StudentSession) -> VisualizationSpec:
    concept = session.concept_history[0] if session.concept_history else None
    diagnosis = session.diagnosis

    if concept is None:
        LOGGER.warning("No concept model in session; using fallback visualization spec")
        return _visualization_fallback(session)

    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")

    # Define standard examples for each concept
    examples = {
        "two-sum-hashmap": "nums=[2,7,11,15], target=9",
        "contains-duplicate": "nums=[1,2,3,1]",
        "valid-anagram": "s='anagram', t='nagaram'",
        "best-time-stock": "prices=[7,1,5,3,6,4]",
        "max-subarray": "nums=[-2,1,-3,4,-1,2,1,-5,4]",
        "valid-parentheses": "s='([]){}'",
        "reverse-linked-list": "head=[1,2,3,4,5]",
        "group-anagrams": "strs=['eat','tea','tan','ate','nat','bat']",
        "product-except-self": "nums=[1,2,3,4]",
        "top-k-frequent": "nums=[1,1,1,2,2,3], k=2",
        "longest-consecutive": "nums=[100,4,200,1,3,2]"
    }
    brief = get_topic_brief(concept_id)
    if brief:
        example_str = (
            f"input/state: {brief.input_display or brief.title}. "
            f"Concrete example to animate step by step: {brief.example_walkthrough}"
        )
        type_rule = (
            "  1. type must be one of 'process', 'timeline', 'flow', or 'comparison' — choose whichever best "
            "matches how this topic's example unfolds (a repeating transformation -> 'process'; a historical or "
            "sequential development -> 'timeline').\n"
            "  2. entities: represent the example's stages, actors, or components as entities (kind: 'node' for "
            "stages, 'array' for ordered values, 'metric' for quantities, 'flow' for processes).\n"
        )
    else:
        example_str = examples.get(concept_id, "nums=[2,7,11,15], target=9")
        type_rule = (
            "  1. type must be exactly 'comparison', 'stack', or 'linked-list' (use 'stack' ONLY if validating brackets/parentheses, use 'linked-list' ONLY if reversing a linked list).\n"
            "  2. entities: include relevant visualization entities representing arrays, strings, stacks, hash-maps, links, nodes, edges, or metrics as appropriate.\n"
        )

    system_prompt = (
        "You are a visualization-design agent for an adaptive learning system. "
        "You produce ONLY a VisualizationSpec JSON that drives a CSS-animated comparison UI.\n"
        f"For the concept '{concept.title}', create a step-by-step visualization spec matching the problem dynamics.\n"
        "Rules:\n"
        + type_rule +
        "  3. states: produce exactly 3 to 5 states (e.g. 'before', 'step-1', 'step-2', 'conclusion') explaining the process. "
        "     Each state has a 'labels' list (1-3 strings) and a 'highlight' list referencing entity ids.\n"
        "  4. transitions: link states sequentially with appropriate animations.\n"
        "  5. questions: exactly 2 to 3 questions covering time complexity, space complexity, and common misconceptions.\n"
        f"  6. Ground the example values in: {example_str}.\n"
        "  7. Do not add fields beyond the schema — but you MUST fill the 'scene' field, which IS part of the schema.\n"
        + _scene_rules("4 to 7 steps")
    )

    user_prompt = json.dumps({
        "concept": concept.model_dump(),
        "diagnostic_report": diagnosis.model_dump() if diagnosis else {},
        "output_type": "VisualizationSpec",
        "topic": concept.title,
        "example": example_str,
        "instruction": (
            f"Produce a VisualizationSpec JSON (including its full 'scene' script) that animates the core mechanism of '{concept.title}' "
            f"step by step. Use the example: {example_str}. "
            "The scene must: (1) Open with a caption stating what problem we're solving and what the input is. "
            "(2) Show each key step with meaningful captions explaining WHAT is happening and WHY. "
            "(3) Close with the concrete answer/result. "
            "Tailor state labels to correct the student's misconceptions listed in diagnostic_report."
        ),
    })

    try:
        spec = call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=VisualizationSpec,
            fallback=lambda: _visualization_fallback(session),
        )
        if concept_id == "two-sum-hashmap":
            spec = _guard_visualization_spec(spec, diagnosis)
        if spec.scene is None or not spec.scene.steps:
            spec.scene = _fallback_scene(session, naive=False)
        log_agent_call(session, "VisualizationAgent", {"llm_spec_id": spec.id, "states": len(spec.states)})
        return spec
    except Exception as exc:
        LOGGER.warning("VisualizationAgent LLM call failed: %s; using fallback", exc)
        fallback = _visualization_fallback(session)
        log_agent_call(session, "VisualizationAgent", {"fallback_used": True})
        return fallback


def visualization_agent_bf_real(session: StudentSession) -> VisualizationSpec:
    concept = session.concept_history[0] if session.concept_history else None
    diagnosis = session.diagnosis

    if concept is None:
        LOGGER.warning("No concept model in session; using brute force fallback visualization spec")
        return _visualization_bf_fallback(session)

    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")

    examples = {
        "two-sum-hashmap": "nums=[2,7,11,15], target=9",
        "contains-duplicate": "nums=[1,2,3,1]",
        "valid-anagram": "s='anagram', t='nagaram'",
        "best-time-stock": "prices=[7,1,5,3,6,4]",
        "max-subarray": "nums=[-2,1,-3,4,-1,2,1,-5,4]",
        "valid-parentheses": "s='([]){}'",
        "reverse-linked-list": "head=[1,2,3,4,5]",
        "group-anagrams": "strs=['eat','tea','tan','ate','nat','bat']",
        "product-except-self": "nums=[1,2,3,4]",
        "top-k-frequent": "nums=[1,1,1,2,2,3], k=2",
        "longest-consecutive": "nums=[100,4,200,1,3,2]"
    }
    brief = get_topic_brief(concept_id)
    if brief:
        example_str = (
            f"input/state: {brief.input_display or brief.title}. "
            f"Concrete naive/initial example to animate step by step: {brief.example_walkthrough}"
        )
    else:
        example_str = examples.get(concept_id, "nums=[2,7,11,15], target=9")

    system_prompt = (
        "You are a visualization-design agent for an adaptive learning system. "
        "You produce ONLY a VisualizationSpec JSON for the brute force/naive approach.\n"
        f"For the concept '{concept.title}', create a step-by-step naive visualization spec.\n"
        "Rules:\n"
        "  1. type must be exactly 'comparison', 'stack', or 'linked-list' (use 'stack' ONLY if validating brackets/parentheses, use 'linked-list' ONLY if reversing a linked list).\n"
        "  2. entities: include relevant visualization entities representing arrays, strings, links, nodes, edges, or metrics.\n"
        "  3. states: produce exactly 3 states (e.g. 'before', 'bf-step', 'conclusion'). "
        "     Each state has a 'labels' list (1-3 strings) and a 'highlight' list referencing entity ids.\n"
        "  4. transitions: link states sequentially.\n"
        "  5. questions: exactly 2 questions asking about the naive time and space complexity.\n"
        f"  6. Ground the example values in: {example_str}.\n"
        "  7. Do not add fields beyond the schema — but you MUST fill the 'scene' field, which IS part of the schema. "
        "The scene must make the naive approach look appropriately laborious (repeated scanning, piling-up counters).\n"
        + _scene_rules("4 to 6 steps")
    )

    user_prompt = json.dumps({
        "concept": concept.model_dump(),
        "diagnostic_report": diagnosis.model_dump() if diagnosis else {},
        "output_type": "VisualizationSpec",
        "instruction": (
            f"Produce a VisualizationSpec JSON (including its full 'scene' script) for the brute-force or "
            f"naive explanation of {concept.title}."
        ),
    })

    try:
        spec = call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=VisualizationSpec,
            fallback=lambda: _visualization_bf_fallback(session),
        )
        if spec.scene is None or not spec.scene.steps:
            spec.scene = _fallback_scene(session, naive=True)
        log_agent_call(session, "VisualizationAgentBF", {"llm_spec_id": spec.id, "states": len(spec.states)})
        return spec
    except Exception as exc:
        LOGGER.warning("VisualizationAgent BF LLM call failed: %s; using fallback", exc)
        return _visualization_bf_fallback(session)


def visualization_agent_stub(session: StudentSession) -> VisualizationSpec:
    log_agent_call(session, "VisualizationAgent", {"active_topic": session.active_topic})
    return VisualizationSpec(
        type="comparison",
        id="two-sum-hashmap-visual",
        title="HashMap lookup vs brute force scan",
        layout={"orientation": "left-right"},
        entities=[
            {"id": "array", "kind": "array", "label": "nums = [2, 7, 11, 15]", "rows": ["2", "7", "11", "15"]},
            {"id": "target", "kind": "metric", "label": "target = 9", "value": 9},
            {"id": "bruteforce", "kind": "flow", "label": "brute force: check every pair"},
            {"id": "hashmap", "kind": "node", "label": "hash map: store seen values"},
            {"id": "lookup", "kind": "node", "label": "lookup complement"}
        ],
        relations=[
            {"from": "array", "to": "bruteforce", "label": "scan all pairs"},
            {"from": "array", "to": "hashmap", "label": "add seen values"},
            {"from": "hashmap", "to": "lookup", "label": "check if target - current exists"}
        ],
        states=[
            {"id": "before", "labels": ["array is unsorted and values are unprocessed"], "highlight": ["array"]},
            {"id": "during", "labels": ["current value 2 -> complement is 7"], "highlight": ["lookup", "hashmap"]},
            {"id": "after", "labels": ["match found without scanning all pairs"], "highlight": ["lookup"]}
        ],
        transitions=[
            {"from": "before", "to": "during", "animation": "highlight-complement", "durationMs": 700},
            {"from": "during", "to": "after", "animation": "resolve-match", "durationMs": 700}
        ],
        questions=[
            {"id": "q1", "prompt": "Why is it faster to check whether target - current is already in a hash map than to compare against every other number?", "expectedObservations": ["You avoid an O(n^2) scan", "Lookup checks one complement directly"]}
        ],
        expectedObservations=[
            "A brute-force approach compares each value with every other value.",
            "A hash map directly checks whether the complement exists.",
            "This reduces the average work from quadratic to linear."
        ]
    )


def practice_agent_real(session: StudentSession) -> ExerciseSet:
    """LLM-powered practice agent that generates topic-specific challenge questions."""
    log_agent_call(session, "PracticeAgent", {"topic": session.active_topic})
    brief = get_topic_brief(session.metadata.get("concept_id", ""))
    concept = session.concept_history[0] if session.concept_history else None
    topic = session.active_topic

    def _fallback() -> ExerciseSet:
        prompt = (
            brief.practice_challenge
            if brief and brief.practice_challenge
            else f"Explain in your own words how {topic} works and why it matters."
        )
        hints = [
            "Think about the key facts shown in the lesson",
            "Walk through the concrete example step by step"
        ]
        return ExerciseSet(
            exercises=[
                ExerciseTask(
                    id="task-1",
                    type="explanation",
                    prompt=prompt,
                    expected_reasoning="; ".join(brief.key_facts) if brief and brief.key_facts else f"Explanation grounded in the core mechanism of {topic}.",
                    hints=hints
                )
            ],
            summary=f"Practice focuses on explaining the core mechanism of {topic} in your own words."
        )

    system_prompt = (
        "You are a practice-question generator for an adaptive learning platform. "
        "Generate ONE open-ended practice question that asks the student to explain the core mechanism "
        "of the topic in their own words, using the concrete example from the lesson. "
        "The question must be answerable by typing a short paragraph (3-6 sentences). "
        "Do NOT ask for code or mathematical derivations — ask for explanation and reasoning. "
        "Return an ExerciseSet JSON with one ExerciseTask (id='task-1', type='explanation'). "
        "The 'expected_reasoning' field should list the key facts the answer must contain. "
        "Include 2-3 progressively more specific hints in the 'hints' array."
    )
    user_prompt = json.dumps({
        "topic": topic,
        "key_facts": (concept.key_facts if concept else (brief.key_facts if brief else [])),
        "example": (brief.example_walkthrough if brief else ""),
        "output_type": "ExerciseSet",
    })
    try:
        result = call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ExerciseSet,
            fallback=_fallback,
        )
        return result
    except Exception:
        return _fallback()


def practice_agent_stub(session: StudentSession) -> ExerciseSet:
    """Alias kept for backward compatibility — now calls the real agent."""
    return practice_agent_real(session)


def _evaluation_fallback(session: StudentSession) -> EvaluationResult:
    return EvaluationResult(
        passed=False,
        score=0.0,
        reasoning_quality="Unable to auto-grade.",
        misconception_detected=[],
        feedback="Auto-grading failed. Marked for manual review."
    )


def evaluation_agent_real(session: StudentSession) -> EvaluationResult:
    concept = session.concept_history[0] if session.concept_history else None
    diagnosis = session.diagnosis
    answers = session.student_answers

    if not concept:
        return _evaluation_fallback(session)

    system_prompt = (
        "You are an expert grading and evaluation agent for a computer science learning platform.\n"
        "Your task is to evaluate the student's answers to checkpoint questions against the ground truth ConceptModel.\n\n"
        "Evaluate the following criteria:\n"
        "1. Factual Correctness: Is the answer correct, partially correct, or incorrect judged against the ConceptModel key facts?\n"
        "2. Reasoning Quality: Does the answer reflect a real understanding of the core concept and optimized solution (based on the ConceptModel key facts), or is it a superficial/correct-sounding guess without justification?\n"
        "3. Misconceptions: Does the answer show the originally suspected misconception (from the DiagnosticReport or Concept misconceptions list), a different misconception, or none?\n\n"
        "Strictly return an EvaluationResult JSON object matching the requested schema."
    )

    user_prompt = json.dumps({
        "concept_key_facts": concept.key_facts,
        "concept_misconceptions": concept.misconceptions,
        "original_diagnosis": diagnosis.model_dump() if diagnosis else {},
        "student_answers": answers,
        "output_type": "EvaluationResult"
    })

    try:
        model = call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=EvaluationResult,
            fallback=lambda: _evaluation_fallback(session),
        )
        return model
    except Exception as exc:
        LOGGER.warning("EvaluationAgent LLM call failed: %s; using fallback", exc)
        return _evaluation_fallback(session)


def _adaptation_fallback(session: StudentSession) -> AdaptationDecision:
    return AdaptationDecision(
        action="continue",
        reason="Let's continue to the next concept.",
        next_step="completed",
        updated_difficulty="moderate"
    )


def adaptation_agent_real(session: StudentSession) -> AdaptationDecision:
    # Find the latest evaluation from agent_trace
    latest_eval = None
    for trace in reversed(session.metadata.get("agent_trace", [])):
        if trace.get("agent") == "EvaluationAgent" and "result" in trace:
            latest_eval = trace["result"]
            break

    diagnosis = session.diagnosis
    concept = session.concept_history[0] if session.concept_history else None

    system_prompt = (
        "You are an adaptive curriculum coordinator agent.\n"
        "Based on the student's EvaluationResult and the original DiagnosticReport, select the next best adaptation action.\n\n"
        "Possible Actions:\n"
        "- 'continue': The student understood the core concepts. Move them to completed.\n"
        "- 'simplify': The student is struggling with basic concepts. Re-explain with simpler terms.\n"
        "- 're-teach': The student has partial understanding but needs a different representation (e.g., compare with brute force).\n"
        "- 'hint': The student is very close but made a minor mistake. Provide a helpful hint.\n"
        "- 'flag_misconception': The student still exhibits the originally suspected misconception or a new one. Address it directly and correct it.\n\n"
        "Provide a short human-readable explanation in the 'reason' field that the student will see directly.\n"
        "Set 'next_step' to:\n"
        "- 'completed' if action is 'continue'\n"
        "- 'visualize' if action is 're-teach', 'hint', 'simplify', or 'flag_misconception' (so they go back to the visualization/practice loop).\n"
        "Set 'updated_difficulty' to 'easy', 'moderate', or 'hard'."
    )

    user_prompt = json.dumps({
        "evaluation_result": latest_eval,
        "original_diagnosis": diagnosis.model_dump() if diagnosis else {},
        "concept": concept.model_dump() if concept else {},
        "output_type": "AdaptationDecision"
    })

    try:
        model = call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=AdaptationDecision,
            fallback=lambda: _adaptation_fallback(session),
        )
        return model
    except Exception as exc:
        LOGGER.warning("AdaptationAgent LLM call failed: %s; using fallback", exc)
        return _adaptation_fallback(session)
