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

TEST_CASES_BATCH2 = {
    "reverse-linked-list": {
        "name": "Reverse Linked List",
        "diagnose_input": "You can reverse a linked list the same way you reverse an array, by swapping values at mirrored positions.",
        "suspected_misconception": "you can reverse a linked list the same way you reverse an array, by swapping values at mirrored positions",
        "practice_input": "To reverse it, I will swap the values of nodes at symmetric indices of the list."
    },
    "group-anagrams": {
        "name": "Group Anagrams",
        "diagnose_input": "We can sort the entire array of strings, and that groups anagrams automatically.",
        "suspected_misconception": "sorting the whole array of strings groups anagrams together automatically",
        "practice_input": "Just sort the array of strings itself to group them together."
    },
    "product-except-self": {
        "name": "Product of Array Except Self",
        "diagnose_input": "You just divide the total product of the array by each element to get the value.",
        "suspected_misconception": "you should just divide the total product by each element",
        "practice_input": "I will calculate the total product of the array and then divide it by nums[i] at each index."
    },
    "top-k-frequent": {
        "name": "Top K Frequent Elements",
        "diagnose_input": "We sort the original array numerically to find the most frequent elements.",
        "suspected_misconception": "sorting the original array numerically finds the most frequent elements",
        "practice_input": "Sort the original array of numbers in numeric order to find the frequent ones."
    },
    "longest-consecutive": {
        "name": "Longest Consecutive Sequence",
        "diagnose_input": "We sort the array first because sorting is required to solve this in linear time.",
        "suspected_misconception": "sorting is required to solve this in linear time",
        "practice_input": "We must sort the array first, which allows scanning for consecutive runs in O(n) time."
    }
}

def verify_problem_batch2(concept_id, config):
    print(f"\n======================================================================")
    print(f" TESTING CONCEPT: {config['name']} ({concept_id})")
    print(f"======================================================================")
    
    # 1. Start Session
    profile = StudentProfile(
        name="Test Candidate Batch 2",
        current_level="beginner",
        self_description=config["diagnose_input"],
        goals=[f"Master {config['name']}"],
        known_concepts=["arrays", "loops"],
        difficult_concepts=[],
        time_budget_minutes=30
    )
    session = start_session(profile, username="candidate_test_batch2", concept_id=concept_id)
    print(f"Started session {session.session_id} for concept ID: {session.metadata['concept_id']}")
    
    # 2. Run Diagnosis
    session.session_status = "diagnose"
    print("Running Learner Diagnosis Agent...")
    diagnosis = diagnostic_agent_real(session)
    session.diagnosis = diagnosis
    print(f"  Suspected Misconceptions: {diagnosis.misconceptions}")
    
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
    print(f"  Entity IDs: {[ent.id for ent in vis_spec.entities]}")
    
    # Validate linked-list primitive for Reverse Linked List
    if concept_id == "reverse-linked-list":
        if vis_spec.type == "linked-list" or any(ent.kind == "node" or ent.kind == "edge" for ent in vis_spec.entities):
            print("  SUCCESS: Reverse Linked List properly produced a linked-list-type or node+edge visualizer layout!")
        else:
            print("  WARNING: Reverse Linked List did NOT produce a linked-list spec. Spec details:")
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

    for concept_id, config in TEST_CASES_BATCH2.items():
        verify_problem_batch2(concept_id, config)
