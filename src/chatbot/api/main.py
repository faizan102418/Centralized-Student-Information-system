"""FastAPI backend.

Run with: uv run uvicorn chatbot.api.main:app --reload --app-dir src
Docs at: http://localhost:8000/docs
"""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from chatbot.api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    LoginRequest,
    TokenResponse,
)
from chatbot.auth import authenticate, create_access_token, decode_access_token
from chatbot.database import get_db_connection
from chatbot.rag_pipeline import answer_question, extract_student_name, setup_vector_db

bearer_scheme = HTTPBearer()

# Simple in-process state for the vector store. For multi-worker production
# deployment this should move to a shared service; fine for a single-process
# deployment at this stage.
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _state["vectorstore"] = setup_vector_db()
    except Exception as exc:  # noqa: BLE001
        # Don't crash the whole app on startup - /health will report the
        # problem instead, which is easier to debug in a container.
        _state["startup_error"] = str(exc)
    yield
    _state.clear()


app = FastAPI(title="Student Record Chatbot API", version="0.2.0", lifespan=lifespan)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    user = decode_access_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _log_query(
    session_id: str,
    user_role: str,
    query_text: str,
    response_text: str,
    latency_ms: int,
    access_denied: bool,
) -> None:
    """Best-effort write to query_logs. Never let logging break the request."""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO query_logs "
            "(session_id, user_role, query_text, detected_intent, system_variant, "
            "response_text, latency_ms, access_denied) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                session_id,
                user_role,
                query_text,
                "lookup" if extract_student_name(query_text) else "general",
                "system",
                response_text,
                latency_ms,
                access_denied,
            ),
        )
        connection.commit()
        connection.close()
    except Exception:  # noqa: BLE001
        pass  # logging failures must never break the chat response


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok" if "vectorstore" in _state else "degraded",
        vector_db_ready="vectorstore" in _state,
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    user = authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(user)
    return TokenResponse(access_token=token, username=user["username"], role=user["role"])


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user: dict = Depends(get_current_user)):
    if "vectorstore" not in _state:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Knowledge base not ready: {_state.get('startup_error', 'unknown error')}",
        )

    start = time.perf_counter()
    response_text = answer_question(_state["vectorstore"], payload.message, user=user)
    latency_ms = int((time.perf_counter() - start) * 1000)

    access_denied = "don't have permission" in response_text
    _log_query(
        session_id=str(uuid.uuid4()),
        user_role=user["role"],
        query_text=payload.message,
        response_text=response_text,
        latency_ms=latency_ms,
        access_denied=access_denied,
    )

    return ChatResponse(response=response_text, latency_ms=latency_ms)
