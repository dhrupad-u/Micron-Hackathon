from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .agents import (
    adaptation_agent_real,
    concept_agent_real,
    diagnostic_agent_real,
    evaluation_agent_real,
    planner_agent_stub,
    practice_agent_stub,
    topic_synthesis_agent,
    visualization_agent_real,
    visualization_agent_bf_real,
)
from .domain import get_concept_node, get_cs_dsa_adapter, get_diagnostic_quiz, register_dynamic_concept
from .image_service import hero_image_url
from .schemas import StudentSession
from .state_store import get_session, save_session


def _attach_quiz_and_hero(session: StudentSession, concept_id: str, title: str, definition: str, key_facts: list[str] | None = None) -> None:
    """Warm-up quiz + hero illustration into session metadata (both best-effort)."""
    quiz = get_diagnostic_quiz(concept_id)
    session.metadata["diagnostic_quiz"] = [q.model_dump() for q in quiz]
    try:
        session.metadata["hero_image_url"] = hero_image_url(concept_id, title, definition, key_facts)
    except Exception:  # noqa: BLE001 — hero art must never break session start
        session.metadata["hero_image_url"] = None


def advance_session(session: StudentSession, answer: str | None = None) -> StudentSession:
    status = session.session_status

    if status == "new":
        if answer:
            session.student_profile.self_description = answer
        session.session_status = "diagnose"
        session.diagnosis = diagnostic_agent_real(session)
        session.session_progress["completed_steps"] = ["diagnose"]
        session.session_progress["next_best_action"] = "plan"
        session.metadata["agent_trace"].append({"step": "diagnose", "agent": "DiagnosticAgent"})
        return save_session(session)

    if status == "diagnose":
        session.session_status = "plan"
        session.learning_plan = planner_agent_stub(session)
        session.session_progress["completed_steps"] = ["diagnose", "plan"]
        session.session_progress["next_best_action"] = "explain"
        session.metadata["agent_trace"].append({"step": "plan", "agent": "PlannerAgent"})
        return save_session(session)

    if status == "plan":
        session.session_status = "explain"
        concept = concept_agent_real(session)
        session.concept_history = [concept]
        session.session_progress["completed_steps"] = ["diagnose", "plan", "explain"]
        session.session_progress["next_best_action"] = "visualize"
        session.metadata["agent_trace"].append({"step": "explain", "agent": "ConceptAgent"})
        return save_session(session)

    if status == "explain":
        session.session_status = "visualize"
        vis_spec = visualization_agent_real(session)
        # Check if topic has genuine dual algorithm comparison (e.g., curated CS/DSA brute force vs hashmap)
        concept = session.concept_history[0] if session.concept_history else None
        concept_id = session.metadata.get("concept_id", "")
        has_dual = (
            concept and concept.methods and len(concept.methods) >= 2 and
            any("brute" in (m.id + m.name).lower() for m in concept.methods) and
            not concept_id.startswith("custom-")
        )
        if has_dual:
            vis_spec_bf = visualization_agent_bf_real(session)
            session.interaction_state["current_visualization_bf"] = vis_spec_bf.model_dump(by_alias=True)
        else:
            session.interaction_state["current_visualization_bf"] = None

        session.interaction_state["current_visualization"] = vis_spec.model_dump(by_alias=True)
        session.session_progress["completed_steps"] = ["diagnose", "plan", "explain", "visualize"]
        session.session_progress["next_best_action"] = "practice"
        session.metadata["agent_trace"].append({"step": "visualize", "agent": "VisualizationAgent"})
        return save_session(session)

    if status == "visualize":
        session.session_status = "practice"
        session.practice_history = [practice_agent_stub(session)]
        session.interaction_state["current_question"] = session.practice_history[0].exercises[0].prompt
        session.session_progress["completed_steps"] = ["diagnose", "plan", "explain", "visualize", "practice"]
        session.session_progress["next_best_action"] = "evaluate"
        session.metadata["agent_trace"].append({"step": "practice", "agent": "PracticeAgent"})
        return save_session(session)

    if status == "practice":
        session.session_status = "evaluate"
        # The typed practice answer is what the Evaluation Agent grades — persist it
        # into student_answers (replacing any prior submission of the same task).
        if answer:
            session.student_answers = [
                a for a in session.student_answers if a.get("question_id") != "practice-task-1"
            ]
            session.student_answers.append({"question_id": "practice-task-1", "answer": answer})
        session.interaction_state["current_feedback"] = "Practice submitted. Evaluating reasoning quality."
        result = evaluation_agent_real(session)
        session.interaction_state["latest_evaluation"] = result.model_dump()
        session.session_progress["mastery_trend"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "score": result.score,
            "passed": result.passed,
        })
        session.metadata["agent_trace"].append({"step": "evaluate", "agent": "EvaluationAgent", "result": result.model_dump()})
        return save_session(session)

    if status == "evaluate":
        session.session_status = "adapt"
        decision = adaptation_agent_real(session)
        session.adaptation_log.append(decision)
        session.session_status = decision.next_step
        session.session_progress["completed_steps"] = ["diagnose", "plan", "explain", "visualize", "practice", "evaluate", "adapt"]
        session.session_progress["next_best_action"] = "completed" if decision.next_step == "completed" else decision.next_step
        session.metadata["agent_trace"].append({"step": "adapt", "agent": "AdaptationAgent", "decision": decision.model_dump()})
        return save_session(session)

    if status == "adapt":
        session.session_status = "completed"
        session.session_progress["completed_steps"].append("completed")
        session.session_progress["next_best_action"] = "none"
        return save_session(session)

    return save_session(session)


def start_session(
    student_profile: Any | None = None,
    username: str | None = None,
    concept_id: str | None = None,
    topic_request: str | None = None,
) -> StudentSession:
    from .state_store import create_session

    session = create_session(student_profile, username=username)
    adapter = get_cs_dsa_adapter()
    session.current_domain = adapter.domain_id
    session.current_subdomain = adapter.subdomain_id

    # Free-text topic request: synthesize a curriculum node for ANY topic on the fly.
    if topic_request and topic_request.strip():
        blueprint = topic_synthesis_agent(
            topic_request,
            student_level=(session.student_profile.current_level if session.student_profile else "beginner"),
        )
        node = register_dynamic_concept(blueprint)
        session.active_topic = node.title
        session.current_domain = node.domain
        session.current_subdomain = node.subdomain
        session.metadata["concept_id"] = node.concept_id
        session.metadata["topic_brief"] = blueprint.model_dump()
        _attach_quiz_and_hero(
            session,
            blueprint.concept_id,
            blueprint.title,
            blueprint.canonical_definition,
            blueprint.key_facts,
        )
        session.metadata["agent_trace"].append({
            "step": "synthesize",
            "agent": "TopicSynthesisAgent",
            "topic_request": topic_request,
        })
        session.session_status = "new"
        return save_session(session)

    target_node = adapter.concept_graph[0]
    if concept_id:
        for node in adapter.concept_graph:
            if node.concept_id == concept_id:
                target_node = node
                break

    session.active_topic = target_node.title
    session.session_status = "new"
    session.metadata["concept_id"] = target_node.concept_id
    _attach_quiz_and_hero(
        session,
        target_node.concept_id,
        target_node.title,
        target_node.canonical_definition,
    )
    return save_session(session)
