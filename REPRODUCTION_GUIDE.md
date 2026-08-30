# Reproduction & Demo Guide

Follow these steps to set up, run, test, and demonstrate the Adaptive Learning Platform.

---

## 1. Setup & Environment
Ensure you have the following environment variables defined in your `backend/.env` file:
```env
# API Key (Supports Groq keys starting with gsk_ or OpenAI/xAI keys)
GROQ_API_KEY=gsk_...
# Model routing
LLM_MODEL=openai/gpt-oss-120b
```

---

## 2. Booting the Application

### Start the Backend (FastAPI)
1. Open a PowerShell/Terminal window.
2. Activate the python virtual environment and run the uvicorn server:
   ```powershell
   cd backend
   .\venv\Scripts\activate
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   *The backend will be running at http://127.0.0.1:8000/*

### Start the Frontend (Vite & React)
1. Open a second PowerShell/Terminal window.
2. Boot Vite:
   ```powershell
   cd frontend
   npm run dev
   ```
   *The frontend will be running at http://localhost:5173/*

---

## 3. Running Automated Verification Scripts
We have two backend verification scripts to test API compliance and grading quality.

### Test 1: Full Session API Verification
Ensures all API endpoints (Sign Up, Log In, Start Session, Advance) transition correctly from `diagnose` all the way to `visualize`:
```powershell
cd backend
.\venv\Scripts\activate
python verify_session_flow.py
```
*Expected Output: `--- ALL BACKEND VERIFICATIONS COMPLETED SUCCESSFULLY ---`*

### Test 2: Pipeline vs. Baseline Grading Comparison
Evaluates three student answers (Correct, Misconception, and Vague) and compares pipeline grading performance on Case B (Misconception) against a baseline direct LLM call:
```powershell
cd backend
.\venv\Scripts\activate
python run_eval_comparison.py
```
*Expected Output: Score calculations, misconception detection lists, and adaptive decisions for Cases A, B, and C.*

### Test 3: Multi-Problem Scaling & Dynamic Loop Closure Verification
Runs the complete multi-agent pipeline (diagnose → explain → visualize → practice → evaluate → adapt) for all 5 new DSA problems, verifying that each problem resolves, explains, and visualizes correctly (specifically checking stack layout validation for Valid Parentheses):
```powershell
cd backend
.\venv\Scripts\activate
python run_five_problems_eval.py
```
*Expected Output: Success flags for contains-duplicate, valid-anagram, best-time-stock, max-subarray, and valid-parentheses, including stack-structure visualization confirmation.*

---

## 4. Live Demo Walkthrough (Video Script)

This is the recommended sequence to demonstrate the platform for submission:

### Step 1: Login & Navigation
1. Open `http://localhost:5173/` in your browser.
2. Sign up with a new username/password.
3. Click **Arrays & Strings** -> choose any of the **6 fully interactive problems** (Two Sum, Contains Duplicate, Valid Anagram, Best Time to Buy and Sell Stock, Maximum Subarray, or Valid Parentheses).
4. Show the new **Problem Statement Screen** containing example inputs, outputs, and constraints matching your selection. Click **Continue to Assessment**.

### Step 2: Diagnostic Assessment
1. Type a basic approach, or click **"I don't know how to solve this — just teach me"** (the beginner route).
2. The orchestrator will diagnose your level, build a custom plan, show the explanation slides, and redirect you to the **Visualization Player**.

### Step 3: Visualization Player
1. Click **Play** to watch the visualizer step through the Hash Map algorithm automatically. Show that the player runs smoothly without interrupting/pausing mid-animation.
2. Click the **Hash Map** tab. Step to the state `bf-step` and highlight that index `[0, 1]` is correctly visual-highlighted for brute-force comparisons.
3. Scroll down to the checkpoint questions. Submit answers or page through multiple questions using the `← Prev Q` and `Next Q →` pagination buttons. Click **Proceed to Practice**.

### Step 4: The Closed-Loop Adaptation
1. Under the **Practice Challenge**, enter a misconception answer like:
   > *"HashMaps are faster because they sort the array when inserting. Once it's sorted, we can search it in O(1) time using binary search."*
2. Click **Submit Practice**. The system will auto-evaluate.
3. Show the **Assessment Results Card**:
   - Score will be `0%`.
   - The Suspected Misconception **"HashMap sorts data"** is caught.
   - The instructor recommendation gives a tailored message correcting you and asks you to **"Try Again"**.
4. Click **Try Again** (takes you back to visualizer).

### Step 5: Complete the Loop
1. View the visualizer again. Go back to Practice.
2. Submit a correct answer:
   > *"A hash map stores seen values. For each number, we do an O(1) average lookup to check if target - current_value is in the map. This avoids nested loops, yielding O(N) average time."*
3. Click **Submit Practice**. The results card will now show **PASSED** (Score 100%) and recommendation **"Finish Session"**.
4. Click **Finish Session** to complete the session!
