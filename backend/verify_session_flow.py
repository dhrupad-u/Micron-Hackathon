import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 1. Sign Up test user 1
signup_resp = client.post(
    "/api/auth/signup",
    json={"username": "user1", "password": "password123"}
)
assert signup_resp.status_code == 200, signup_resp.text
auth_data1 = signup_resp.json()
token1 = auth_data1["token"]
print("SIGNUP User 1 SUCCESS: Token =", token1)

# 2. Login test user 1
login_resp = client.post(
    "/api/auth/login",
    json={"username": "user1", "password": "password123"}
)
assert login_resp.status_code == 200, login_resp.text
auth_data1 = login_resp.json()
token1 = auth_data1["token"]
print("LOGIN User 1 SUCCESS")

# 3. Sign Up test user 2 (for scoping check)
signup_resp2 = client.post(
    "/api/auth/signup",
    json={"username": "user2", "password": "password456"}
)
assert signup_resp2.status_code == 200, signup_resp2.text
auth_data2 = signup_resp2.json()
token2 = auth_data2["token"]
print("SIGNUP User 2 SUCCESS")

# 4. Start session for user 1 (needs auth header)
headers1 = {"Authorization": f"Bearer {token1}"}
start_resp = client.post(
    "/api/session/start",
    json={
        "student_profile": {
            "name": "user1",
            "current_level": "beginner",
            "goals": ["Learn why HashMap makes Two Sum faster"],
            "known_concepts": ["arrays", "loops"],
            "difficult_concepts": ["hash map semantics"],
            "time_budget_minutes": 25,
        }
    },
    headers=headers1
)
assert start_resp.status_code == 200, start_resp.text
state = start_resp.json()
session_id = state["session_id"]
print("START SESSION SUCCESS. Session ID =", session_id)

# 5. Access session of user 1 without authorization header -> expect 401
unauth_resp = client.post(
    "/api/session/advance",
    json={"session_id": session_id}
)
assert unauth_resp.status_code == 401
print("VERIFIED: Unauthorized request correctly returns 401")

# 6. Access session of user 1 with user 2's token -> expect 403
headers2 = {"Authorization": f"Bearer {token2}"}
forbidden_resp = client.post(
    "/api/session/advance",
    json={"session_id": session_id},
    headers=headers2
)
assert forbidden_resp.status_code == 403
print("VERIFIED: Session scoping breach correctly returns 403")

# 7. Advance session of user 1 with correct token
# Step 1: Diagnose (new -> diagnose)
adv_resp = client.post(
    "/api/session/advance",
    json={"session_id": session_id, "answer": "I would use a hash map complement lookup"},
    headers=headers1
)
assert adv_resp.status_code == 200, adv_resp.text
state = adv_resp.json()
print("STEP 1: Diagnose => Status:", state["session_status"])
assert state["student_profile"]["self_description"] == "I would use a hash map complement lookup"
print("VERIFIED: Typed approach correctly saved to student profile self-description")

# Step 2: Plan (diagnose -> plan)
adv_resp = client.post(
    "/api/session/advance",
    json={"session_id": session_id},
    headers=headers1
)
assert adv_resp.status_code == 200, adv_resp.text
state = adv_resp.json()
print("STEP 2: Plan => Status:", state["session_status"])

# Step 3: Explain (plan -> explain)
adv_resp = client.post(
    "/api/session/advance",
    json={"session_id": session_id},
    headers=headers1
)
assert adv_resp.status_code == 200, adv_resp.text
state = adv_resp.json()
print("STEP 3: Explain => Status:", state["session_status"])

# Confirm concept model methods list is present (LLM may name the optimized
# method 'hashmap', 'hash-map', 'optimized', etc., so match like the frontend does)
methods = state["concept_history"][0]["methods"]
method_ids = [m["id"] for m in methods]
brute = [i for i in method_ids if "brute" in i.lower() or "naive" in i.lower()]
optimized = [i for i in method_ids if i not in brute]
assert len(methods) >= 2, f"Concept model must have at least 2 methods, got {len(methods)}"
assert brute, f"no brute-force method found, got {method_ids}"
assert optimized, f"no optimized method found, got {method_ids}"
print(f"VERIFIED: Concept model contains the methods list ({', '.join(method_ids)})")

# Step 4: Visualize (explain -> visualize)
adv_resp = client.post(
    "/api/session/advance",
    json={"session_id": session_id},
    headers=headers1
)
assert adv_resp.status_code == 200, adv_resp.text
state = adv_resp.json()
print("STEP 4: Visualize => Status:", state["session_status"])

# Confirm dual visualization specs are generated
assert state["interaction_state"]["current_visualization"] is not None
assert state["interaction_state"]["current_visualization_bf"] is not None
print("VERIFIED: Dual visualization specs generated for both brute-force and hashmap methods")

print("\n--- ALL BACKEND VERIFICATIONS COMPLETED SUCCESSFULLY ---")
