import json
import os
import sys

# Add current folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.schemas import StudentSession, StudentProfile, ConceptModel, DiagnosticReport, MethodModel, EvaluationResult, AdaptationDecision
from app.agents import evaluation_agent_real, adaptation_agent_real, log_agent_call
from app.domain import get_cs_dsa_adapter

def get_base_session(student_answer: str, suspected_misconceptions=None):
    if suspected_misconceptions is None:
        suspected_misconceptions = []
        
    adapter = get_cs_dsa_adapter()
    node = adapter.concept_graph[0]
    
    # 1. Create Profile
    profile = StudentProfile(
        name="Test Student",
        current_level="beginner",
        self_description="I want to learn Two Sum",
        goals=["Learn why HashMap makes Two Sum faster"],
        known_concepts=["arrays", "loops"],
        difficult_concepts=["hash map semantics"],
        time_budget_minutes=25
    )
    
    # 2. Create ConceptModel
    concept = ConceptModel(
        concept_id=node.concept_id,
        title=node.title,
        canonical_definition=node.canonical_definition,
        key_facts=[
            "Brute force compares each value with every other value — quadratic work.",
            "A hash map stores seen values and checks if target - current_value exists in constant average O(1) time.",
            "The speedup comes from replacing linear scanning with constant average lookup.",
            "Average lookup in a hash map is O(1), so the algorithm becomes O(N) average time."
        ],
        prerequisites=node.prerequisites,
        misconceptions=node.misconceptions,
        explanation_summary="The speedup comes from replacing linear scans with constant average time lookups of the complement. The map does not sort values.",
        teaching_emphasis=["lookup semantics vs sorting", "complement check"],
        methods=[]
    )
    
    # 3. Create DiagnosticReport
    diagnosis = DiagnosticReport(
        understanding=["arrays", "loops"],
        missing_prerequisites=["hash map lookup semantics"],
        misconceptions=suspected_misconceptions,
        confidence=0.8,
        summary="Suspecting student might confuse HashMap lookup with sorting if flagged."
    )
    
    # 4. Create Session
    session = StudentSession(
        session_id="test-session-123",
        student_profile=profile,
        session_status="practice",
        diagnosis=diagnosis,
        concept_history=[concept],
        student_answers=[
            {"question_id": "q1", "answer": student_answer}
        ]
    )
    
    return session

def run_pipeline(label, answer, suspected_misconceptions=None):
    print(f"\n=======================================================")
    print(f" RUNNING PIPELINE: {label}")
    print(f"=======================================================")
    print(f"Student Answer: \"{answer}\"")
    
    session = get_base_session(answer, suspected_misconceptions)
    
    # Run Evaluation
    print("\nRunning Evaluation Agent...")
    eval_res = evaluation_agent_real(session)
    print(f"  Passed: {eval_res.passed}")
    print(f"  Score: {eval_res.score}")
    print(f"  Reasoning Quality: {eval_res.reasoning_quality}")
    print(f"  Misconceptions Detected: {eval_res.misconception_detected}")
    print(f"  Feedback: {eval_res.feedback}")
    
    # Record in agent trace for adaptation agent to retrieve
    session.metadata["agent_trace"].append({
        "step": "evaluate",
        "agent": "EvaluationAgent",
        "result": eval_res.model_dump()
    })
    
    # Run Adaptation
    print("\nRunning Adaptation Agent...")
    adapt_res = adaptation_agent_real(session)
    print(f"  Action: {adapt_res.action}")
    print(f"  Rationale/Message: {adapt_res.reason}")
    print(f"  Next Step: {adapt_res.next_step}")
    print(f"  Difficulty: {adapt_res.updated_difficulty}")
    
    return eval_res, adapt_res

def run_baseline_grading(label, answer):
    print(f"\n=======================================================")
    print(f" RUNNING BASELINE DIRECT LLM CALL ON: {label}")
    print(f"=======================================================")
    print(f"Student Answer: \"{answer}\"")
    
    # Simple direct LLM call setup using openai library
    import openai
    from dotenv import load_dotenv
    load_dotenv()
    
    key = os.getenv("XAI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")
    is_groq = bool(key and key.startswith("gsk_"))
    
    if is_groq:
        client = openai.OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        model_name = os.getenv("LLM_MODEL") or "openai/gpt-oss-120b"
    else:
        # fallback to direct openai endpoint
        client = openai.OpenAI(api_key=key)
        model_name = os.getenv("LLM_MODEL") or "gpt-4o-mini"
        
    print(f"Direct LLM call with model {model_name}...")
    
    prompt = (
        f"Grade this student's explanation for why a hash map is faster than brute force for Two Sum:\n"
        f"\"{answer}\"\n\n"
        f"Respond in a simple format indicating:\n"
        f"1. Is it correct? (Yes/No)\n"
        f"2. Score (0.0 to 1.0)\n"
        f"3. Misconceptions detected\n"
        f"4. Brief feedback"
    )
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        print("\nBaseline Response:")
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"Baseline call failed: {e}")

if __name__ == "__main__":
    # Force output encoding to support any special chars
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
        
    # Case A: Correct, well-reasoned answer
    case_a_ans = "A hash map stores values we have already seen. As we scan, we can check if the complement (target - current_value) is already in the map in O(1) average time. This avoids double looping, making it O(N) average time instead of O(N^2) brute force."
    run_pipeline("Case A: Correct, well-reasoned answer", case_a_ans)
    
    # Case B: Misconception answer ("HashMap sorts data")
    case_b_ans = "HashMaps are faster because they sort the array when inserting. Once it's sorted, we can search it in O(1) time using binary search."
    run_pipeline("Case B: HashMap sorts data misconception", case_b_ans, ["HashMap sorts data"])
    
    # Case C: Vague/uncertain answer
    case_c_ans = "I think it is faster because it does some hashing lookup, but I am not really sure how it computes the index or why it is O(1) instead of searching."
    run_pipeline("Case C: Vague/uncertain answer", case_c_ans)
    
    # Case D: Plausible-sounding wrong answer (Hashing target sum)
    case_d_ans = "HashMaps are fast because they use a hashing function to map the target sum to a specific index, allowing us to find the two numbers in O(1) time."
    run_pipeline("Case D: Plausible-sounding wrong answer (Hashing target sum)", case_d_ans, ["Hashing target sum instead of elements"])
    
    # Run Baseline comparisons
    run_baseline_grading("Case B (HashMap sorts data)", case_b_ans)
    run_baseline_grading("Case D (Hashing target sum)", case_d_ans)
