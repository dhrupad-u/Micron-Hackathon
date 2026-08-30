from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import DiagnosticReport, ConceptModel


def run_case(label: str, text: str) -> None:
    client = TestClient(app)
    start = client.post(
        "/api/session/start",
        json={
            "student_profile": {
                "name": "Demo Student",
                "current_level": "beginner",
                "self_description": text,
                "goals": ["Learn why HashMap makes Two Sum faster"],
                "known_concepts": ["arrays", "loops"],
                "difficult_concepts": ["hash map semantics"],
                "time_budget_minutes": 25,
            }
        },
    )
    session = start.json()
    session_id = session["session_id"]

    # start -> diagnose -> plan -> explain must all happen before the ConceptAgent output is present
    for _ in range(3):
        updated = client.post("/api/session/advance", json={"session_id": session_id})
        session = updated.json()

    diagnosis = session["diagnosis"]
    concept = session["concept_history"][0]

    print(f"CASE: {label}")
    print("DIAGNOSTIC REPORT:")
    print(DiagnosticReport(**diagnosis).model_dump_json(indent=2))
    print("CONCEPT MODEL:")
    print(ConceptModel(**concept).model_dump_json(indent=2))
    print("---")


run_case(
    "1. Understands loops and arrays, no clear misconception",
    "I understand loops and arrays but I don't know why HashMaps make Two Sum faster.",
)
run_case(
    "2. HashMaps sort data misconception",
    "I think HashMaps just sort the data so lookups are faster.",
)
run_case(
    "3. Very low confidence / beginner",
    "I don't really know anything about this.",
)
