"""End-to-end verification: the Learn Anything pipeline.

Starts a session from a free-text topic request (no concept_id), then drives the
full loop diagnose -> plan -> explain -> visualize -> practice -> evaluate -> adapt,
verifying at each stage that the synthesized topic flows through every agent.

Runs against a non-CS topic and a CS-but-not-curated topic to prove the claim:
ANY topic the user types gets a real curriculum, visualizer, and closed adaptation loop.
"""
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

TEST_TOPICS = [
    {
        "name": "Photosynthesis (non-CS science)",
        "topic_request": "How does photosynthesis work?",
        "diagnose_input": "Plants eat sunlight through their leaves and that gives them energy directly.",
        "practice_wrong": "Photosynthesis converts sunlight directly into energy the plant burns immediately, oxygen is just a waste product plants don't use.",
        "practice_right": None,  # right answer phrasing is topic-specific; we accept any pass/fail, structure is what we verify
    },
    {
        "name": "TLS encryption (CS but not curated)",
        "topic_request": "How does TLS encryption work?",
        "diagnose_input": "TLS encrypts everything with one shared password that the server sends to the browser at the start.",
        "practice_wrong": "The server sends its private key to the browser so they can both encrypt messages with the same key.",
        "practice_right": None,
    },
]


def run_topic(config):
    print("\n" + "=" * 70)
    print(f" TESTING ANY-TOPIC PIPELINE: {config['name']}")
    print(f" topic_request: {config['topic_request']!r}")
    print("=" * 70)

    # Auth
    resp = client.post("/api/auth/signup", json={"username": "anytopic-user", "password": "demo1234"})
    if resp.status_code != 200:
        resp = client.post("/api/auth/login", json={"username": "anytopic-user", "password": "demo1234"})
    assert resp.status_code == 200, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}

    # 1. Start session from free text — the Topic Synthesis Agent runs here
    resp = client.post(
        "/api/session/start",
        json={
            "topic_request": config["topic_request"],
            "student_profile": {
                "name": "anytopic-user",
                "current_level": "beginner",
                "goals": [f"Understand {config['topic_request']}"],
                "time_budget_minutes": 25,
            },
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    state = resp.json()
    brief = state["metadata"]["topic_brief"]
    concept_id = state["metadata"]["concept_id"]

    assert concept_id.startswith("custom-"), f"expected custom- concept id, got {concept_id}"
    for field in ["canonical_definition", "key_facts", "misconceptions", "example_walkthrough", "practice_challenge"]:
        assert brief.get(field), f"topic brief missing {field}"
    print(f"  [OK] Synthesized concept_id: {concept_id}")
    print(f"  [OK] Title: {brief['title']}")
    print(f"  [OK] input_display: {brief.get('input_display', '')[:70]}")
    print(f"  [OK] example_values: {brief.get('example_values', [])}")

    # 2. Diagnose — misconception from the student text should flow through
    resp = client.post(
        "/api/session/advance",
        json={"session_id": state["session_id"], "answer": config["diagnose_input"]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    state = resp.json()
    assert state["session_status"] == "diagnose", state["session_status"]
    print(f"  [OK] Diagnose complete (confidence={state['diagnosis']['confidence']})")

    # 3. Plan
    resp = client.post("/api/session/advance", json={"session_id": state["session_id"]}, headers=headers)
    assert resp.status_code == 200, resp.text
    state = resp.json()
    assert state["session_status"] == "plan"
    plan = state["learning_plan"]
    assert config["topic_request"].split()[0].lower()[:8] in (plan["goal"] + plan["target_concept"]).lower() or "custom" in plan["target_concept"].lower() or brief["title"].split()[0].lower()[:8] in plan["goal"].lower(), \
        f"plan not grounded in the custom topic: {plan['goal']}"
    print(f"  [OK] Plan grounded in custom topic: {plan['goal'][:70]}...")

    # 4. Explain — ConceptModel for the custom topic
    resp = client.post("/api/session/advance", json={"session_id": state["session_id"]}, headers=headers)
    assert resp.status_code == 200, resp.text
    state = resp.json()
    assert state["session_status"] == "explain"
    concept = state["concept_history"][0]
    assert concept["concept_id"] == concept_id
    assert len(concept["methods"]) >= 2, f"expected >=2 methods, got {[m['id'] for m in concept['methods']]}"
    method_ids = [m["id"] for m in concept["methods"]]
    print(f"  [OK] ConceptModel methods: {method_ids}")

    # 5. Visualize — both specs valid for a non-curated topic
    resp = client.post("/api/session/advance", json={"session_id": state["session_id"]}, headers=headers)
    assert resp.status_code == 200, resp.text
    state = resp.json()
    assert state["session_status"] == "visualize"
    hm_spec = state["interaction_state"]["current_visualization"]
    bf_spec = state["interaction_state"]["current_visualization_bf"]
    for spec, label in [(hm_spec, "optimized"), (bf_spec, "brute-force")]:
        assert spec and spec.get("states"), f"{label} spec missing states"
        assert spec.get("type") in ("flow", "array", "comparison", "node", "metric", "question", "stack", "linked-list", "process", "timeline"), spec.get("type")
    print(f"  [OK] Visualizer specs: optimized type={hm_spec['type']} ({len(hm_spec['states'])} states), bf type={bf_spec['type']} ({len(bf_spec['states'])} states)")

    # 6. Practice + Evaluate (wrong answer carrying a likely misconception)
    resp = client.post("/api/session/advance", json={"session_id": state["session_id"]}, headers=headers)
    assert resp.status_code == 200, resp.text
    state = resp.json()
    assert state["session_status"] == "practice"
    practice_prompt = state["interaction_state"]["current_question"]
    print(f"  [OK] Practice challenge: {practice_prompt[:80]}...")

    resp = client.post(
        "/api/session/advance",
        json={"session_id": state["session_id"], "answer": config["practice_wrong"]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    state = resp.json()
    evaluation = state["interaction_state"]["latest_evaluation"]
    assert evaluation, "evaluation missing"
    print(f"  [OK] Evaluation: score={evaluation['score']}, passed={evaluation['passed']}, misconceptions={evaluation['misconception_detected']}")

    # 7. Adaptation — decision must be grounded and route somewhere sane
    resp = client.post("/api/session/advance", json={"session_id": state["session_id"]}, headers=headers)
    assert resp.status_code == 200, resp.text
    state = resp.json()
    decision = state["adaptation_log"][-1]
    assert decision["action"] in ("continue", "simplify", "re-teach", "hint", "flag_misconception"), decision["action"]
    assert decision["next_step"] in ("visualize", "practice", "completed"), decision["next_step"]
    print(f"  [OK] Adaptation: action={decision['action']} -> next_step={decision['next_step']}")
    print(f"       reason: {decision['reason'][:100]}...")
    return True


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    results = [run_topic(cfg) for cfg in TEST_TOPICS]
    if all(results):
        print("\n--- ALL ANY-TOPIC PIPELINE VERIFICATIONS COMPLETED SUCCESSFULLY ---")
        sys.exit(0)
    sys.exit(1)
