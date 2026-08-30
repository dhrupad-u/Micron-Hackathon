from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict

from .schemas import StudentSession, StudentProfile


SESSIONS: Dict[str, StudentSession] = {}
USERS: Dict[str, Dict[str, str]] = {}  # username -> {"hashed_password": ..., "salt": ...}
TOKENS: Dict[str, str] = {}            # token -> username


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if not salt:
        salt = uuid.uuid4().hex
    hashed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return hashed, salt


def create_user(username: str, password: str) -> str | None:
    if username in USERS:
        return None
    hashed, salt = hash_password(password)
    USERS[username] = {"hashed_password": hashed, "salt": salt}
    token = uuid.uuid4().hex
    TOKENS[token] = username
    return token


def authenticate_user(username: str, password: str) -> str | None:
    if username not in USERS:
        return None
    user = USERS[username]
    hashed, _ = hash_password(password, user["salt"])
    if hashed == user["hashed_password"]:
        token = uuid.uuid4().hex
        TOKENS[token] = username
        return token
    return None


def get_user_from_token(token: str | None) -> str | None:
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[7:]
    return TOKENS.get(token)


def create_session(student_profile: StudentProfile | None = None, username: str | None = None) -> StudentSession:
    profile = student_profile or StudentProfile()
    if username:
        profile.name = username
    
    # Generate unique session ID instead of static "session-001"
    session_id = f"session-{uuid.uuid4().hex[:8]}"
    
    session = StudentSession(
        session_id=session_id,
        student_profile=profile,
        username=username,
        metadata={
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "agent_trace": []
        }
    )
    SESSIONS[session.session_id] = session
    return session


def get_session(session_id: str) -> StudentSession:
    return SESSIONS[session_id]


def save_session(session: StudentSession) -> StudentSession:
    session.metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
    SESSIONS[session.session_id] = session
    return session
