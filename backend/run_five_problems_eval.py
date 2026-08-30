import json
import os
import sys

# Add current folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.schemas import StudentSession, StudentProfile, ConceptModel, DiagnosticReport, MethodModel, EvaluationResult, AdaptationDecision
from app.agents import (
    diagnostic_agent_real,
    concept_agent_real,
    visualization_agent_real,
    evaluation_agent_real,
    adaptation_agent_real
)
from app.orchestrator import start_session

# Test configurations for the 5 new problems
TEST_CASES = {
    "contains-duplicate": {
        "name": "Contains Duplicate",
        "diagnose_input": "We can just sort the array first, then compare adjacent elements. It's the only way.",
        "suspected_misconception": "sorting is the only way to solve this",
        "practice_input": "I still think we have to sort the array first to compare neighbors."
    },
    "valid-anagram": {
        "name": "Valid Anagram",
        "diagnose_input": "We can just check if both strings have the exact same set of unique characters.",
        "suspected_misconception": "checking that both strings contain the same set of unique characters is sufficient",
        "practice_input": "Just verify that both strings have the same set of unique letters."
    },
    "best-time-stock": {
        "name": "Best Time to Buy and Sell Stock",
        "diagnose_input": "We just search the array to find the global lowest price and buy there, and sell at the highest price.",
        "suspected_misconception": "you must buy at the lowest price in the entire array regardless of when it occurs",
        "practice_input": "You buy at the absolute minimum price and sell at the maximum."
    },
    "max-subarray": {
        "name": "Maximum Subarray",
        "diagnose_input": "We can track a running sum and reset it to 0 whenever it becomes negative.",
        "suspected_misconception": "the running sum should reset to 0 whenever it goes negative",
        "practice_input": "Reset the current running sum to 0 whenever it goes negative."
    },
    "valid-parentheses": {
        "name": "Valid Parentheses",
        "diagnose_input": "We can just count the opening and closing brackets, and if the count matches, it's valid.",
        "suspected_misconception": "just counting the number of opening and closing brackets being equal is enough",
        "practice_input": "Just verify that open brackets count equals close brackets count."
    }
}

def verify_problem(concept_id, config):
    print(f"\n======================================================================")
    print(f" TESTING CONCEPT: {config['name']} ({concept_id})")
    print(f"======================================================================")
    
    # 1. Start Session
    profile = StudentProfile(
        name="Test Candidate",
        current_level="beginner",
        self_description=config["diagnose_input"],
        goals=[f"Master {config['name']}"],
        known_concepts=["arrays", "loops"],
        difficult_concepts=[],
        time_budget_minutes=30
    )
    session = start_session(profile, username="candidate_test", concept_id=concept_id)
    print(f"Started session {session.session_id} for concept ID: {session.metadata['concept_id']}")
    
    # 2. Run Diagnosis
    session.session_status = "diagnose"
    print("Running Learner Diagnosis Agent...")
    diagnosis = diagnostic_agent_real(session)
    session.diagnosis = diagnosis
    print(f"  Suspected Misconceptions: {diagnosis.misconceptions}")
    print(f"  Confidence: {diagnosis.confidence}")
    
    # 3. Run Concept Agent
    session.session_status = "explain"
    print("\nRunning Concept Agent...")
    concept = concept_agent_real(session)
    session.concept_history = [concept]
    print(f"  Title: {concept.title}")
    print(f"  Methods Generated:")
    for method in concept.methods:
        print(f"    - ID: {method.id} | Name: {method.name} | Complexity: Time {method.complexity.get('time')}, Space {method.complexity.get('space')}")
    
    # 4. Run Visualization Agent
    session.session_status = "visualize"
    print("\nRunning Visualization Agent...")
    vis_spec = visualization_agent_real(session)
    print(f"  Spec Title: {vis_spec.title}")
    print(f"  Spec Type: {vis_spec.type}")
    print(f"  State IDs: {[st.id for st in vis_spec.states]}")
    print(f"  Transition count: {len(vis_spec.transitions)}")
    print(f"  Entity IDs: {[ent.id for ent in vis_spec.entities]}")
    
    # Validate Stack Spec for Valid Parentheses
    if concept_id == "valid-parentheses":
        if vis_spec.type == "stack" or any(ent.kind == "stack" for ent in vis_spec.entities):
            print("  SUCCESS: Valid Parentheses properly produced a stack-type/stack-entity specification!")
        else:
            print("  WARNING: Valid Parentheses did NOT produce a stack specification. Spec details:")
            print(json.dumps(vis_spec.model_dump(by_alias=True), indent=2))
            
    # 5. Run Evaluation Agent
    session.session_status = "evaluate"
    session.student_answers = [
        {"question_id": "q1", "answer": config["practice_input"]}
    ]
    print("\nRunning Evaluation Agent with misconception input...")
    print(f"  Student Practice Input: \"{config['practice_input']}\"")
    eval_res = evaluation_agent_real(session)
    print(f"  Passed: {eval_res.passed}")
    print(f"  Score: {eval_res.score}")
    print(f"  Misconceptions Detected: {eval_res.misconception_detected}")
    print(f"  Tutoring Feedback: {eval_res.feedback}")
    
    # Record in trace
    session.metadata["agent_trace"].append({
        "step": "evaluate",
        "agent": "EvaluationAgent",
        "result": eval_res.model_dump()
    })
    
    # 6. Run Adaptation Agent
    session.session_status = "adapt"
    print("\nRunning Adaptation Agent...")
    adapt_res = adaptation_agent_real(session)
    print(f"  Action Decision: {adapt_res.action}")
    print(f"  Curriculum Pivot Message: {adapt_res.reason}")
    print(f"  Routed Next Step: {adapt_res.next_step}")
    print(f"  Adjusted Difficulty: {adapt_res.updated_difficulty}")

if __name__ == "__main__":
    # Force output encoding to support any special chars
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    for concept_id, config in TEST_CASES.items():
        verify_problem(concept_id, config)
