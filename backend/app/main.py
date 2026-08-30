from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .orchestrator import advance_session, start_session
from .schemas import (
    AnswerRequest,
    SessionAdvanceRequest,
    SessionStartRequest,
    StudentSession,
    AuthRequest,
    AuthResponse,
    ChatAskRequest,
    ChatAskResponse,
)
from .state_store import (
    get_session,
    save_session,
    create_user,
    authenticate_user,
    get_user_from_token,
)

app = FastAPI(title="Adaptive Learning Agent Auth")

_IMAGES_DIR = Path(__file__).resolve().parent.parent / "generated_images"
_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/images", StaticFiles(directory=str(_IMAGES_DIR)), name="images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(request: AuthRequest) -> AuthResponse:
    if not request.username.strip() or not request.password.strip():
        raise HTTPException(status_code=400, detail="Username and password cannot be empty")
    token = create_user(request.username, request.password)
    if not token:
        raise HTTPException(status_code=400, detail="Username already exists")
    return AuthResponse(token=token, username=request.username)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: AuthRequest) -> AuthResponse:
    token = authenticate_user(request.username, request.password)
    if not token:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    return AuthResponse(token=token, username=request.username)


@app.post("/api/session/start", response_model=StudentSession)
def start_api_session(
    request: SessionStartRequest | None = None,
    authorization: str | None = Header(None),
) -> StudentSession:
    username = get_user_from_token(authorization)
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    profile = request.student_profile if request else None
    concept_id = request.concept_id if request else None
    topic_request = request.topic_request if request else None
    return start_session(profile, username=username, concept_id=concept_id, topic_request=topic_request)


@app.post("/api/session/advance", response_model=StudentSession)
def advance_api_session(
    request: SessionAdvanceRequest,
    authorization: str | None = Header(None),
) -> StudentSession:
    username = get_user_from_token(authorization)
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    session = get_session(request.session_id)
    if session.username != username:
        raise HTTPException(status_code=403, detail="Forbidden: Session ownership mismatch")
    return advance_session(session, answer=request.answer)


@app.post("/api/session/answer", response_model=StudentSession)
def submit_answer(
    request: AnswerRequest,
    authorization: str | None = Header(None),
) -> StudentSession:
    username = get_user_from_token(authorization)
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    session = get_session(request.session_id)
    if session.username != username:
        raise HTTPException(status_code=403, detail="Forbidden: Session ownership mismatch")
    # Remove any prior answer for the same question_id, then append
    session.student_answers = [
        a for a in session.student_answers if a.get("question_id") != request.question_id
    ]
    session.student_answers.append({
        "question_id": request.question_id,
        "answer": request.answer,
    })
    return save_session(session)


@app.post("/api/chat/ask", response_model=ChatAskResponse)
def ask_chat_assistant(
    request: ChatAskRequest,
    authorization: str | None = Header(None),
) -> ChatAskResponse:
    from .agents import chat_assistant_agent

    username = get_user_from_token(authorization)
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    session = get_session(request.session_id)
    if session.username != username:
        raise HTTPException(status_code=403, detail="Forbidden: Session ownership mismatch")

    return chat_assistant_agent(
        session=session,
        user_question=request.user_question,
        current_screen=request.current_screen,
    )
