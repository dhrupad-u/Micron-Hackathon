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
    VisualizationClassifier,
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
    _tf = TopicBlueprint(
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
    )

    # Topic-aware fallback quiz built from the blueprint's own facts/misconceptions.
    facts = [f for f in _tf.key_facts]
    myths = [m for m in _tf.misconceptions]
    tokens = _tf.example_values
    quiz = []
    if facts and len(myths) >= 2:
        opts = [facts[0], myths[0], myths[1], f"{title} has no cause-and-effect structure"]
        quiz.append(QuizQuestion(
            question=f"Which statement about {title} is actually TRUE?",
            options=opts,
            correct_index=0,
            misconception_tag=myths[0][:60],
            explanation=facts[0],
        ))
    if len(facts) > 1 and len(myths) >= 3:
        opts = [facts[1], myths[2], "It works differently every time, with no rules", "Only experts can ever trace how it works"]
        quiz.append(QuizQuestion(
            question=f"Someone claims: '{myths[2] if len(myths) > 2 else myths[0]}' — what's the best response?",
            options=opts,
            correct_index=0,
            misconception_tag=myths[2][:60] if len(myths) > 2 else myths[0][:60],
            explanation=facts[1],
        ))
    if len(tokens) >= 3:
        quiz.append(QuizQuestion(
            question=f"In a concrete run of {title}, which stage follows '{tokens[0]}'?",
            options=[tokens[1], tokens[2], tokens[0], "the process restarts from scratch"],
            correct_index=0,
            misconception_tag="sequence not understood",
            explanation=f"The mechanism runs {tokens[0]} → {tokens[1]} → {tokens[2]}.",
        ))
    if len(quiz) < 3:
        quiz.append(QuizQuestion(
            question=f"What's the smartest way to actually understand {title}?",
            options=[
                "Trace one concrete example end to end",
                "Memorize the definition word for word",
                "Skip the mechanism and learn buzzwords",
                "Assume it works like everything else",
            ],
            correct_index=0,
            misconception_tag="memorization over mechanism",
            explanation="Tracing a concrete example exposes the actual cause-and-effect chain.",
        ))
    _tf.diagnostic_quiz = quiz[:3]
    return _tf


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
        "Each question must test real domain intuitions for THIS specific topic (e.g. for Supply & Demand, test price adjustments when supply drops; for WiFi, test radio wave transmission; for black holes, test what happens to light near the event horizon). "
        "Every question and option must mention concrete entities of the topic itself (objects, forces, steps, values). "
        "FORBIDDEN: questions about 'inputs' and 'outputs' as abstract words, 'step 1 vs step 2', how the app works, or any meta/placeholder phrasing — those are instant failures. "
        "Make at least one question a mini-scenario: 'If X happens, what does the topic predict?' "
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


def _visualization_classifier(topic_title: str, concept_text: str) -> VisualizationClassifier:
    system_prompt = (
        "You are a visualization-type classifier for an adaptive learning system. "
        "Given a topic and its concept description, choose the best visualization renderer.\n"
        "RENDERERS:\n"
        "  - emoji-scene: algorithms, processes, sequences, step-by-step procedures, code flows. "
        "Actors move on a grid with emoji icons. Best for: sorting, searching, data structures, programming, cooking recipes, manufacturing steps.\n"
        "  - graph: quantitative relationships with axes, curves, or data trends. Best for: economics (supply/demand), physics (motion/forces), math (functions), chemistry (reaction rates), biology (population growth), any topic with 'X vs Y' or equilibrium.\n"
        "  - diagram: structural or hierarchical concepts with labeled parts and connections. Best for: biology (cell structure), chemistry (molecular structure), history (causes/effects), systems (org charts, networks), anatomy, geography.\n"
        "  - image-overlay: real-world phenomena best shown with a photo + animated labels. Best for: geography (earthquakes), medicine (surgery), astronomy (planets), mechanics (engines), anything spatial or physical.\n"
        "Output renderer and a 1-sentence reasoning."
    )
    user_prompt = json.dumps({
        "topic": topic_title,
        "concept_description": concept_text[:400] if concept_text else topic_title,
        "output_type": "VisualizationClassifier",
    })
    def _fallback() -> VisualizationClassifier:
        topic_lower = (topic_title or "").lower()
        if any(k in topic_lower for k in ["supply", "demand", "economics", "market", "price", "curve", "equilibrium"]):
            return VisualizationClassifier(renderer="graph", reasoning="Quantitative curves/axes detected")
        if any(k in topic_lower for k in ["cell", "molecule", "anatomy", "biology", "chemistry", "structure"]):
            return VisualizationClassifier(renderer="diagram", reasoning="Structural diagram detected")
        return VisualizationClassifier(renderer="emoji-scene", reasoning="Default process/sequence")
    try:
        return call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=VisualizationClassifier,
            fallback=_fallback,
        )
    except Exception:
        return _fallback()


def _scene_rules(step_range: str, renderer: str = "emoji-scene") -> str:
    base = (
        "SCENE RULES — the required 'scene' field (this drives the animated visual the student watches):\n"
        "  CRITICAL — This is an EDUCATIONAL animation. A student watching ONLY this animation must understand:\n"
        "  1) what is being shown, 2) the key mechanism/insight, 3) the final concrete result.\n"
        "  FRAMING (all three required):\n"
        "    - scene.problem: ONE sentence stating the concrete problem with real values.\n"
        "    - scene.goal: ONE sentence telling the student what to watch for.\n"
        "    - scene.takeaway: ONE sentence with the concrete final result.\n"
        "  - scene.background: a one-word theme: 'sky', 'lab', 'grid', 'nature', 'space', or 'default'.\n"
    )

    if renderer == "graph":
        return base + (
            "  RENDERER: 'graph' — axes + curves + points + annotations.\n"
            "  You MUST populate 'graph_data' with this exact structure:\n"
            "    graph_data = {\n"
            "      x_axis: string, y_axis: string, x_range: [number, number], y_range: [number, number],\n"
            "      curves: [{ id, type: 'supply'|'demand'|'line'|'curve', label, points: [[x,y],...], color: '#hex' }],\n"
            "      equilibria: [{ id, x, y, label, color, visible_from_step, visible_to_step }],\n"
            "      annotations: [{ text, x, y, step, color }]\n"
            "    }\n"
            "  RULES: Points must use the SAME coordinate space as x_range/y_range. "
            "Use clear colors (#1cb0f6, #22c55e, #ef4444, #f59e0b). "
            "Supply/demand: use type='supply' or 'demand'. Equilibrium points mark where curves cross. "
            "Annotations appear at specific steps to explain shifts.\n"
            "  scene.actors: 4-8 actors labeling axes, curves, and key points (not data points themselves).\n"
            "  scene.steps: " + step_range + ". Each step has:\n"
            "    * caption: ONE short sentence (max 110 chars) with real values.\n"
            "    * narration: 1-2 sentences explaining WHY.\n"
            "    * effects: use 'highlight', 'dim', 'pulse' on curve/axis actors. Do NOT use 'move' for curve data — curve movement is handled by graph_data visibility and annotations.\n"
            "  FORBIDDEN: abstract labels like 'input 1', 'step 1', 'process'. Every label must name a REAL entity in this topic.\n"
        )

    if renderer == "diagram":
        return base + (
            "  RENDERER: 'diagram' — labeled structural components with connections.\n"
            "  scene.actors: 4-8 actors representing REAL PARTS of this topic. "
            "Use kind='node' for major components, kind='box' for sub-parts, kind='arrow' for connectors. "
            "Labels must be the ACTUAL names from this domain (e.g. 'Mitochondria', 'French Revolution', 'HTTP').\n"
            "  scene.steps: " + step_range + ". Each step has:\n"
            "    * caption: ONE short sentence stating WHAT changes.\n"
            "    * narration: 1-2 sentences explaining the mechanism.\n"
            "    * effects: use 'appear', 'highlight', 'connect', 'pulse', 'dim'. "
            "'connect' links two actors with a dashed line to show relationship.\n"
            "  Step 0 = all parts appear labeled. Final step = the full mechanism is shown and highlighted.\n"
            "  FORBIDDEN: generic labels like 'part A', 'component 1', 'stage 1'. Use real domain terminology.\n"
        )

    if renderer == "image-overlay":
        return base + (
            "  RENDERER: 'image-overlay' — base image with animated labels/annotations.\n"
            "  scene.actors: 3-6 actors representing LABELS/ANNOTATIONS that will appear over an image. "
            "Use kind='chip' or 'box' for labels, kind='arrow' for pointing indicators. "
            "Labels must be SHORT (max 20 chars) and SPECIFIC to the concept.\n"
            "  scene.steps: " + step_range + ". Each step has:\n"
            "    * caption: ONE short sentence about what the annotation explains.\n"
            "    * narration: 1-2 sentences connecting the label to the mechanism.\n"
            "    * effects: use 'appear', 'move', 'highlight', 'pulse' to place labels on the image.\n"
            "  Step 0 = initial labels appear. Final step = all key features are labeled and the takeaway is proven.\n"
            "  NOTE: The base image is generated separately. Your actors are OVERLAYS only.\n"
            "  FORBIDDEN: generic labels like 'area 1', 'part A'. Use real feature names.\n"
        )

    # Default: emoji-scene
    return base + (
        "  RENDERER: 'emoji-scene' — actors on a percentage grid with emoji/icons.\n"
        "  scene.actors: 3 to 8 actors. Each actor is a MEANINGFUL part of THIS concept — never a decorative placeholder.\n"
        "    Actor fields: id (kebab-case), kind from " + _SCENE_KINDS + "; "
        "a SHORT label (max 12 chars) naming its ROLE in this specific concept; an emoji 'icon' relevant to the concept; "
        "x and y on a 0-100 percentage grid (y=10 top, y=90 bottom; keep x within 12-88, y within 15-85); "
        "optional 'value' (number) for counters/meters. Data actors (boxes/chips) must carry the REAL example values as labels.\n"
        "  - scene.steps: " + step_range + ". Each step has:\n"
        "    * caption: ONE short sentence (max 110 chars) stating WHAT changes, with real values.\n"
        "    * narration: 1-2 sentences explaining WHY this happens and what it proves.\n"
        "    * effects: 1-4 effects that MUTATE the stage (move actors, fill labels, increment counters, highlight the actor the caption talks about).\n"
        "    * Step 0 = the problem setup (actors with real input values appear). Final step = the outcome (the answer actor/result is highlighted, takeaway proven on stage).\n"
        "  - Each effect: 'actor' (an actor id), 'action' from " + _SCENE_ACTIONS + "; for 'move' set to_x/to_y (0-100);\n"
        "for 'split'/'merge'/'connect'/'emit' set 'target' to the partner actor id; 'label'/'value' update the actor's text/number.\n"
        "  FORBIDDEN: captions or labels like 'step 1', 'input 1', 'input 2', 'process', 'something changes' — every caption must be about THIS topic's real content.\n"
    )


_CURATED_EXAMPLES = {
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
    "longest-consecutive": "nums=[100,4,200,1,3,2]",
}


def _two_sum_scene(naive: bool) -> SceneScript:
    """Hand-crafted, genuinely explanatory scene for the flagship demo topic."""
    values = ["2", "7", "11", "15"]
    n = len(values)
    x0 = 20.0
    actors = [
        SceneActor(id=f"box-{i}", kind="box", label=v, x=x0 + i * 17, y=32)
        for i, v in enumerate(values)
    ]
    actors.append(SceneActor(id="target", kind="chip", label="target = 9", icon="🎯", x=84, y=18))
    actors.append(SceneActor(id="scanner", kind="arrow", label="current", icon="👇", x=x0, y=50))
    if naive:
        actors.append(SceneActor(id="pairs", kind="counter", label="comparisons", icon="🔁", value=0, x=50, y=78))
        steps = [
            SceneStep(
                id="s0", caption="Problem: find two numbers here that add up to 9.",
                narration="The brute-force idea is simple: try every possible pair and check its sum. Correct — but how much work is it?",
                effects=[SceneEffect(actor=f"box-{i}", action="appear") for i in range(n)]
                + [SceneEffect(actor="target", action="appear"), SceneEffect(actor="scanner", action="appear")],
            ),
        ]
        comparisons = 0
        for i in range(n):
            for j in range(i + 1, n):
                comparisons += 1
                steps.append(SceneStep(
                    id=f"s-{i}-{j}",
                    caption=f"Compare {values[i]} + {values[j]} = {int(values[i]) + int(values[j])}"
                    + ("  ✅ found it!" if int(values[i]) + int(values[j]) == 9 else " — not 9."),
                    narration=(
                        f"This single check costs one comparison. With n numbers there are n·(n−1)/2 ≈ {n * (n - 1) // 2} "
                        "such pairs — that's O(n²): the work explodes as the array grows."
                        if int(values[i]) + int(values[j]) == 9
                        else f"No match, so we try the next pair. Each 'no' still costs a full comparison — brute force pays for every guess."
                    ),
                    effects=[SceneEffect(actor="scanner", action="move", to_x=x0 + i * 17, to_y=50)]
                    + [SceneEffect(actor=f"box-{i}", action="highlight"), SceneEffect(actor=f"box-{j}", action="highlight"),
                       SceneEffect(actor="pairs", action="increment", value=comparisons)],
                ))
        steps.append(SceneStep(
            id="s-end", caption=f"Done: {comparisons} comparisons to be sure. That's O(n²).",
            narration="Imagine a million numbers — a trillion comparisons. We can do much better.",
            effects=[SceneEffect(actor="pairs", action="pulse")],
        ))
        return SceneScript(
            background="grid",
            problem="Find two numbers in [2, 7, 11, 15] that add up to 9.",
            goal="Watch the comparison counter — brute force pays for every pair it tries.",
            takeaway="Brute force needed 6 comparisons for 4 numbers: correct, but O(n²) — it doesn't scale.",
            actors=actors, steps=steps,
        )

    # Optimized: hash map one-pass
    actors.append(SceneActor(id="map", kind="node", label="hash map", icon="🗂️", x=22, y=74))
    actors.append(SceneActor(id="chip-0", kind="chip", label="", icon="", x=48, y=74))
    actors.append(SceneActor(id="chip-1", kind="chip", label="", icon="", x=62, y=74))
    actors.append(SceneActor(id="answer", kind="counter", label="pair found", icon="✅", value=0, x=84, y=74))
    seen = ["2", "7", "11", "15"]
    steps = [
        SceneStep(
            id="s0", caption="Problem: find two numbers that add up to 9 — in ONE pass.",
            narration="The trick: as we visit each number, we ask 'have I already seen its partner (9 − current)?' The hash map answers in O(1) average time.",
            effects=[SceneEffect(actor=f"box-{i}", action="appear") for i in range(n)]
            + [SceneEffect(actor="target", action="appear"), SceneEffect(actor="scanner", action="appear"),
               SceneEffect(actor="map", action="appear"), SceneEffect(actor="answer", action="appear")],
        ),
    ]
    # trace: 2 (need 7, store 2) → 7 (need 2, FOUND)
    steps.append(SceneStep(
        id="s1", caption="Take 2: is its partner 9−2=7 in the map? Not yet.",
        narration="The map only contains what we've already walked past. 7 isn't there — so we remember 2 and move on. No sorting, no comparing with every other element.",
        effects=[SceneEffect(actor="scanner", action="move", to_x=x0, to_y=50), SceneEffect(actor="box-0", action="highlight"),
                 SceneEffect(actor="map", action="pulse"), SceneEffect(actor="chip-0", action="appear", label="2")],
    ))
    steps.append(SceneStep(
        id="s2", caption="Take 7: is its partner 9−7=2 in the map? YES!",
        narration="Instead of re-scanning the array for 2, one direct map lookup proves 2 was seen before. That single lookup replaces an entire nested loop — this is the whole insight.",
        effects=[SceneEffect(actor="scanner", action="move", to_x=x0 + 17, to_y=50), SceneEffect(actor="box-1", action="highlight"),
                 SceneEffect(actor="chip-0", action="pulse"), SceneEffect(actor="answer", action="increment", value=1)],
    ))
    steps.append(SceneStep(
        id="s3", caption="Answer: 2 + 7 = 9, found in 2 steps, not 6.",
        narration="We never touched 11 or 15. One pass, one small map: O(n) average time, O(n) extra space — memory buys speed.",
        effects=[SceneEffect(actor="answer", action="pulse"), SceneEffect(actor="chip-1", action="appear", label="done")],
    ))
    return SceneScript(
        background="grid",
        problem="Find two numbers in [2, 7, 11, 15] that add up to 9 — but in a single pass.",
        goal="Watch the hash map: it remembers every number already seen, so each partner check is instant.",
        takeaway="Answer: 2 + 7 = 9 at indices 0 and 1 — one pass, O(n) average time. The map never sorts anything; it just remembers.",
        actors=actors, steps=steps,
    )


def _supply_demand_scene() -> SceneScript:
    supply_points = [(10, 8), (25, 5), (40, 3), (55, 1.5)]
    demand_points = [(10, 1), (25, 3), (40, 5), (55, 8)]
    shifted_supply = [(20, 8), (35, 5), (50, 3), (65, 1.5)]

    actors = [
        SceneActor(id="x-axis", kind="arrow", label="Quantity", icon="", x=50, y=90),
        SceneActor(id="y-axis", kind="arrow", label="Price ($)", icon="", x=12, y=50),
        SceneActor(id="d-curve", kind="node", label="Demand", icon="📉", x=65, y=22),
        SceneActor(id="s1-curve", kind="node", label="Supply", icon="📈", x=28, y=68),
        SceneActor(id="s2-curve", kind="node", label="Supply (shifted)", icon="📈", x=28, y=68),
        SceneActor(id="e1", kind="token", label="E1: $3, 40 units", icon="🔵", x=50, y=50),
        SceneActor(id="e2", kind="token", label="E2: $5, 25 units", icon="🔴", x=38, y=42),
        SceneActor(id="price-tag", kind="chip", label="", icon="", x=50, y=18),
    ]

    steps = [
        SceneStep(
            id="s0",
            caption="Market starts at equilibrium E1: price $3, quantity 40.",
            narration="Supply and demand curves cross where the market clears — every orange for sale finds a buyer at $3.",
            effects=[
                SceneEffect(actor="x-axis", action="appear"),
                SceneEffect(actor="y-axis", action="appear"),
                SceneEffect(actor="d-curve", action="appear"),
                SceneEffect(actor="s1-curve", action="appear"),
                SceneEffect(actor="e1", action="appear"),
                SceneEffect(actor="price-tag", action="fill", label="$3"),
            ],
        ),
        SceneStep(
            id="s1",
            caption="Heatwave destroys crops → orange supply drops at every price.",
            narration="Sellers now have fewer oranges to sell. The whole supply curve shifts left (or up): S1 becomes S2.",
            effects=[
                SceneEffect(actor="s1-curve", action="shift_curve", to_x=38, to_y=68, label="Supply (shifted)"),
                SceneEffect(actor="s2-curve", action="appear"),
                SceneEffect(actor="s1-curve", action="disappear"),
            ],
        ),
        SceneStep(
            id="s2",
            caption="New intersection E2: price rises to $5, quantity falls to 25.",
            narration="Scarcity bids up the price. At $5, only 25 oranges trade — the market clears again, but fewer people buy.",
            effects=[
                SceneEffect(actor="e2", action="appear"),
                SceneEffect(actor="e1", action="dim"),
                SceneEffect(actor="s2-curve", action="highlight"),
                SceneEffect(actor="d-curve", action="highlight"),
                SceneEffect(actor="e2", action="highlight"),
                SceneEffect(actor="price-tag", action="fill", label="$5"),
            ],
        ),
        SceneStep(
            id="s3",
            caption="Takeaway: a supply drop raises price and lowers quantity sold.",
            narration="This is the core supply-demand mechanism: curve shifts change both price and quantity, not just one.",
            effects=[
                SceneEffect(actor="e2", action="pulse"),
                SceneEffect(actor="price-tag", action="pulse"),
            ],
        ),
    ]

    return SceneScript(
        renderer="graph",
        background="grid",
        problem="A heatwave reduces orange supply. What happens to price and quantity?",
        goal="Watch the supply curve shift left and track the new equilibrium.",
        takeaway="Supply drop → higher equilibrium price, lower quantity sold.",
        actors=actors,
        steps=steps,
        graph_data={
            "x_axis": "Quantity of Oranges",
            "y_axis": "Price ($)",
            "x_range": [0, 80],
            "y_range": [0, 10],
            "curves": [
                {
                    "id": "d-curve",
                    "type": "demand",
                    "label": "Demand (D)",
                    "points": demand_points,
                    "color": "#1cb0f6",
                },
                {
                    "id": "s1-curve",
                    "type": "supply",
                    "label": "Supply (S1)",
                    "points": supply_points,
                    "color": "#22c55e",
                },
                {
                    "id": "s2-curve",
                    "type": "supply",
                    "label": "Supply (S2)",
                    "points": shifted_supply,
                    "color": "#f59e0b",
                    "visible_from_step": 2,
                },
            ],
            "equilibria": [
                {"id": "e1", "x": 40, "y": 3, "label": "E1", "color": "#3b82f6", "visible_from_step": 1, "visible_to_step": 2},
                {"id": "e2", "x": 25, "y": 5, "label": "E2", "color": "#ef4444", "visible_from_step": 3},
            ],
            "annotations": [
                {"text": "Supply shifts left", "x": 45, "y": 72, "step": 2, "color": "#f59e0b"},
                {"text": "Price ↑", "x": 8, "y": 52, "step": 3, "color": "#ef4444"},
                {"text": "Quantity ↓", "x": 18, "y": 85, "step": 3, "color": "#ef4444"},
            ],
        },
    )


def _graph_fallback_scene(session: StudentSession) -> SceneScript:
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    node = get_concept_node(concept_id)
    topic = session.active_topic or node.title
    x_label = "Input / Cause"
    y_label = "Output / Effect"
    if "price" in topic.lower() or "demand" in topic.lower() or "supply" in topic.lower():
        x_label = "Quantity"
        y_label = "Price"
    elif "force" in topic.lower() or "acceleration" in topic.lower():
        x_label = "Force (N)"
        y_label = "Acceleration (m/s²)"
    elif "time" in topic.lower() or "distance" in topic.lower():
        x_label = "Time"
        y_label = "Distance"

    return SceneScript(
        renderer="graph",
        background="grid",
        problem=f"Visualize the core relationship in {topic}.",
        goal="Watch the curve move from the starting state to the outcome.",
        takeaway=f"The key insight of {topic} is the relationship between {x_label.lower()} and {y_label.lower()}.",
        actors=[
            SceneActor(id="x-axis", kind="arrow", label=x_label, icon="", x=50, y=90),
            SceneActor(id="y-axis", kind="arrow", label=y_label, icon="", x=12, y=50),
            SceneActor(id="line-before", kind="node", label="Before", icon="🔵", x=25, y=65),
            SceneActor(id="line-after", kind="node", label="After", icon="🔴", x=65, y=35),
        ],
        steps=[
            SceneStep(
                id="s0",
                caption=f"Starting state: {topic} at baseline.",
                narration=f"We observe {topic} from its initial conditions.",
                effects=[
                    SceneEffect(actor="x-axis", action="appear"),
                    SceneEffect(actor="y-axis", action="appear"),
                    SceneEffect(actor="line-before", action="appear"),
                ],
            ),
            SceneStep(
                id="s1",
                caption=f"A change occurs in {topic}.",
                narration=f"The key mechanism shifts the relationship between {x_label.lower()} and {y_label.lower()}.",
                effects=[
                    SceneEffect(actor="line-after", action="appear"),
                    SceneEffect(actor="line-before", action="dim"),
                    SceneEffect(actor="line-after", action="highlight"),
                ],
            ),
            SceneStep(
                id="s2",
                caption=f"Result: {topic} resolves at a new state.",
                narration=f"The final outcome shows how {topic} adapts and stabilizes.",
                effects=[
                    SceneEffect(actor="line-after", action="pulse"),
                ],
            ),
        ],
        graph_data={
            "x_axis": x_label,
            "y_axis": y_label,
            "x_range": [0, 100],
            "y_range": [0, 100],
            "curves": [
                {
                    "id": "line-before",
                    "type": "line",
                    "label": "Before",
                    "points": [[10, 70], [30, 60], [50, 50], [70, 40]],
                    "color": "#1cb0f6",
                    "visible_from_step": 0,
                    "visible_to_step": 1,
                },
                {
                    "id": "line-after",
                    "type": "line",
                    "label": "After",
                    "points": [[10, 40], [30, 35], [50, 30], [70, 20]],
                    "color": "#ef4444",
                    "visible_from_step": 1,
                },
            ],
            "equilibria": [],
            "annotations": [
                {"text": "Change", "x": 45, "y": 55, "step": 1, "color": "#f59e0b"},
            ],
        },
    )


def _diagram_fallback_scene(session: StudentSession) -> SceneScript:
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    node = get_concept_node(concept_id)
    topic = session.active_topic or node.title
    words = topic.replace("&", "and").split()[:3]
    safe = [w.strip(",.:;") for w in words if w.strip(",.:;")]
    a = safe[0] if safe else "Part A"
    b = safe[1] if len(safe) > 1 else "Part B"
    c = safe[2] if len(safe) > 2 else "Result"

    return SceneScript(
        renderer="diagram",
        background="lab",
        problem=f"Understand the structure of {topic}.",
        goal="Watch how the parts connect and produce the whole.",
        takeaway=f"{topic} is a system of connected parts: {a}, {b}, and {c}.",
        actors=[
            SceneActor(id="a", kind="node", label=a, icon="🔵", x=25, y=40),
            SceneActor(id="b", kind="node", label=b, icon="🟢", x=50, y=40),
            SceneActor(id="c", kind="node", label=c, icon="🔴", x=75, y=40),
        ],
        steps=[
            SceneStep(
                id="s0",
                caption=f"Parts of {topic}: {a}, {b}, {c}.",
                narration="Every system is made of connected components.",
                effects=[
                    SceneEffect(actor="a", action="appear"),
                    SceneEffect(actor="b", action="appear"),
                    SceneEffect(actor="c", action="appear"),
                ],
            ),
            SceneStep(
                id="s1",
                caption=f"{a} connects to {b}, which connects to {c}.",
                narration=f"The mechanism of {topic} flows through these connections.",
                effects=[
                    SceneEffect(actor="a", action="connect", target="b"),
                    SceneEffect(actor="b", action="connect", target="c"),
                ],
            ),
            SceneStep(
                id="s2",
                caption=f"Together they form {topic}.",
                narration=f"This is the complete structure: every part has a role.",
                effects=[
                    SceneEffect(actor="a", action="pulse"),
                    SceneEffect(actor="b", action="pulse"),
                    SceneEffect(actor="c", action="pulse"),
                ],
            ),
        ],
    )


def _image_overlay_fallback_scene(session: StudentSession) -> SceneScript:
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    node = get_concept_node(concept_id)
    topic = session.active_topic or node.title
    return SceneScript(
        renderer="image-overlay",
        background="default",
        problem=f"Explore {topic} with labeled annotations.",
        goal="Watch each label appear and explain a key feature.",
        takeaway=f"Key features of {topic} are shown and explained step by step.",
        actors=[
            SceneActor(id="lbl-1", kind="chip", label="Feature 1", icon="🏷️", x=30, y=30),
            SceneActor(id="lbl-2", kind="chip", label="Feature 2", icon="🏷️", x=60, y=50),
            SceneActor(id="lbl-3", kind="chip", label="Feature 3", icon="🏷️", x=40, y=70),
        ],
        steps=[
            SceneStep(
                id="s0",
                caption=f"Overview of {topic}.",
                narration="We'll annotate the key features one by one.",
                effects=[
                    SceneEffect(actor="lbl-1", action="appear"),
                ],
            ),
            SceneStep(
                id="s1",
                caption="Second feature appears.",
                narration="Each annotation highlights a specific mechanism.",
                effects=[
                    SceneEffect(actor="lbl-2", action="appear"),
                    SceneEffect(actor="lbl-1", action="highlight"),
                ],
            ),
            SceneStep(
                id="s2",
                caption="Third feature completes the picture.",
                narration="All features together explain the whole concept.",
                effects=[
                    SceneEffect(actor="lbl-3", action="appear"),
                    SceneEffect(actor="lbl-2", action="highlight"),
                    SceneEffect(actor="lbl-3", action="highlight"),
                ],
            ),
        ],
    )


def _fallback_scene(session: StudentSession, naive: bool = False, renderer: str = "emoji-scene") -> SceneScript:
    """Deterministic scenes: hand-crafted for two-sum, renderer-aware fallbacks otherwise."""
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    topic = (session.active_topic or "").lower()
    if concept_id == "two-sum-hashmap":
        return _two_sum_scene(naive)

    if renderer == "graph":
        return _graph_fallback_scene(session)
    if renderer == "diagram":
        return _diagram_fallback_scene(session)
    if renderer == "image-overlay":
        return _image_overlay_fallback_scene(session)

    if any(k in topic for k in ["supply", "demand", "economics", "market", "price"]):
        return _supply_demand_scene()

    brief = get_topic_brief(concept_id)
    if brief and brief.example_values:
        tokens = [str(t)[:10] for t in brief.example_values[:5]]
        problem = f"Understand how {brief.title} actually works, one stage at a time."
        goal = "Watch each stage appear in order and connect to the next — the mechanism is the sequence, not any single box."
        takeaway = brief.example_walkthrough.split(".")[0] if brief.example_walkthrough else "Each stage feeds the next — that chain is the mechanism."
    else:
        tokens = ["start", "change", "result"]
        problem = f"See how {session.active_topic} unfolds, stage by stage."
        goal = "Watch the sequence: each stage sets up the next one."
        takeaway = "The final stage is the outcome of the whole chain."

    n = len(tokens)
    x0 = max(16.0, 50 - (n - 1) * 11)
    actors = [
        SceneActor(id=f"stage-{i}", kind="box", label=t, icon="", x=x0 + i * 22, y=42)
        for i, t in enumerate(tokens)
    ]
    actors.append(SceneActor(id="flow", kind="arrow", label="next", icon="👉", x=x0, y=66))
    steps: list[SceneStep] = [
        SceneStep(
            id="s0", caption=problem,
            narration=goal,
            effects=[SceneEffect(actor=f"stage-{i}", action="appear") for i in range(n)]
            + [SceneEffect(actor="flow", action="appear")],
        )
    ]
    for i in range(n):
        steps.append(SceneStep(
            id=f"s{i + 1}",
            caption=f"Stage {i + 1}: {tokens[i]}" + (" — the starting point." if i == 0 else " builds on what came before."),
            narration=(
                "Each stage exists because the previous one produced something this stage needs. "
                "If you can say what each stage hands to the next one, you understand the mechanism."
                if i > 0 else
                "Everything that follows depends on this initial state."
            ),
            effects=[SceneEffect(actor="flow", action="move", to_x=x0 + i * 22, to_y=66),
                     SceneEffect(actor=f"stage-{i}", action="pulse")],
        ))
    steps.append(SceneStep(
        id=f"s{n + 1}", caption=takeaway,
        narration="That is the whole story: a chain of cause and effect, not a list of isolated facts.",
        effects=[SceneEffect(actor=f"stage-{n - 1}", action="highlight")],
    ))
    return SceneScript(
        background="nature" if brief else "default",
        problem=problem, goal=goal, takeaway=takeaway,
        actors=actors, steps=steps,
    )


def _visualization_fallback(session: StudentSession, renderer: str = "emoji-scene") -> VisualizationSpec:
    concept_id = session.metadata.get("concept_id", "two-sum-hashmap")
    node = get_concept_node(concept_id)

    vis_type = "comparison"

    states = [
        VisualizationState(
            id="before",
            labels=[f"Start: {node.title} initial state."],
            highlight=["input"]
        ),
        VisualizationState(
            id="step-1",
            labels=[f"Key mechanism in action."],
            highlight=["optimized"]
        ),
        VisualizationState(
            id="conclusion",
            labels=[f"Result: {node.title} resolved."],
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
            VisualizationEntity(id="optimized", kind="node", label="core process"),
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
                prompt=f"What is the key mechanism in {node.title}?",
                expectedObservations=["The core transformation or relationship"]
            )
        ],
        expectedObservations=[],
        renderer=renderer,
        scene=_fallback_scene(session, naive=False, renderer=renderer),
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
    brief = get_topic_brief(concept_id)
    example_str = (
        f"input/state: {brief.input_display or brief.title}. "
        f"Concrete example to animate step by step: {brief.example_walkthrough}"
    ) if brief else "nums=[2,7,11,15], target=9"

    # Classify topic into a renderer type
    classifier = _visualization_classifier(concept.title, concept.canonical_definition)
    renderer = classifier.renderer
    LOGGER.info("VisualizationClassifier: topic='%s' -> renderer='%s' (%s)", concept.title, renderer, classifier.reasoning)

    scene_rules = _scene_rules("4 to 7 steps", renderer=renderer)

    system_prompt = (
        "You are a visualization-design agent for an adaptive learning system. "
        "You produce ONLY a VisualizationSpec JSON that drives a renderer-aware visualization UI.\n"
        f"For the concept '{concept.title}', create a step-by-step visualization spec.\n"
        "Rules:\n"
        f"  1. renderer must be exactly '{renderer}'. "
        "This is already chosen by a classifier — do NOT override it.\n"
        "  2. type must be one of: 'process', 'timeline', 'flow', 'comparison'. Choose the best fit.\n"
        "  3. entities: represent the example's stages, actors, or components as entities (kind: 'node' for stages, 'array' for ordered values, 'metric' for quantities, 'flow' for processes).\n"
        "  4. states: produce exactly 3 to 5 states explaining the process. Each state has 'labels' and 'highlight'.\n"
        "  5. transitions: link states sequentially with appropriate animations.\n"
        "  6. questions: exactly 2 to 3 questions covering key intuitions and common misconceptions for THIS specific topic.\n"
        f"  7. Ground the example values in: {example_str}.\n"
        "  8. Do not add fields beyond the schema — but you MUST fill the 'scene' field, which IS part of the schema.\n"
        + scene_rules
    )

    user_prompt = json.dumps({
        "concept": {
            "title": concept.title,
            "canonical_definition": concept.canonical_definition,
            "key_facts": concept.key_facts,
            "teaching_emphasis": concept.teaching_emphasis,
            "deep_mechanism": concept.deep_mechanism,
            "narrative_intuition": concept.narrative_intuition,
        },
        "student_misconceptions": (diagnosis.misconceptions if diagnosis else []),
        "chosen_renderer": renderer,
        "output_type": "VisualizationSpec",
        "example": example_str,
        "instruction": (
            f"Produce a VisualizationSpec JSON with renderer='{renderer}' and a full 'scene' script. "
            f"Animate the core mechanism of '{concept.title}' step by step. Use the example: {example_str}. "
            "The scene must: (1) Open with a caption stating what problem we're solving and what the input is. "
            "(2) Show each key step with meaningful captions explaining WHAT is happening and WHY. "
            "(3) Close with the concrete answer/result. "
            "Correct the student's misconceptions in step narrations where relevant. "
            f"Because renderer='{renderer}', follow its schema EXACTLY as described in the system prompt."
        ),
    })

    try:
        spec = call_structured_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=VisualizationSpec,
            fallback=lambda: _visualization_fallback(session, renderer=renderer),
        )
        if concept_id == "two-sum-hashmap":
            spec = _guard_visualization_spec(spec, diagnosis)

        # Force the classifier's renderer into the spec so frontend dispatches correctly
        spec.renderer = renderer
        if spec.scene is None or not spec.scene.steps:
            spec.scene = _fallback_scene(session, naive=False, renderer=renderer)
        elif spec.scene and spec.scene.renderer != renderer:
            spec.scene.renderer = renderer

        log_agent_call(session, "VisualizationAgent", {"llm_spec_id": spec.id, "renderer": renderer, "states": len(spec.states)})
        return spec
    except Exception as exc:
        LOGGER.warning("VisualizationAgent LLM call failed: %s; using fallback", exc)
        fallback = _visualization_fallback(session, renderer=renderer)
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
        "concept": {
            "title": concept.title,
            "canonical_definition": concept.canonical_definition,
            "key_facts": concept.key_facts,
            "method_summaries": [f"{m.name} — {m.complexity.get('time', 'n/a')} time" for m in (concept.methods or [])],
        },
        "student_misconceptions": (diagnosis.misconceptions if diagnosis else []),
        "output_type": "VisualizationSpec",
        "example": example_str,
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
