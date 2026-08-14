# adk_agent_app/server.py
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .config import FIRESTORE_SESSION_DB, PROJECT_ID
from .runner import APP_NAME, create_sosta_runner, execute_turn

FRONTEND_CHAT_HTML_PATH = Path(__file__).resolve().parent / "frontend" / "chat.html"
FRONTEND_GUIDE_HTML_PATH = Path(__file__).resolve().parent / "frontend" / "guide.html"

app = FastAPI(
    title="SostaApp Production Runner API",
    description="FastAPI wrapper around the ADK 2.0 Runner backed by FirestoreSessionService and FirestoreMemoryService.",
    version="6.1.0",
)

# Singleton production Runner instance
sosta_runner = create_sosta_runner()


class ChatRequest(BaseModel):
    user_id: str = Field(
        default="guest",
        description="Caller identifier (e.g., 'guest' for new users, or 'usr_0a8f67' for registered users).",
    )
    session_id: str = Field(
        ...,
        description="Conversation session ID persisted in Firestore (`adk-agent-dev-session-memory-fs`).",
    )
    message: str = Field(
        ...,
        description="User message for the current turn.",
    )
    save_to_memory: bool = Field(
        default=False,
        description="If true, commits the session to long-term MemoryService after this turn.",
    )
    persist_memory: bool | None = Field(
        default=None,
        description="Alias for save_to_memory: if true, commits the session to long-term MemoryService after this turn.",
    )


class ChatResponse(BaseModel):
    session_id: str
    user_id: str
    author: str
    response: str
    tool_calls: List[Dict[str, Any]]
    session_state: Dict[str, Any]


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/chat", response_class=HTMLResponse, include_in_schema=False)
async def chat_ui() -> HTMLResponse:
    """Serves the interactive SostaApp Production Runner Chat UI from `adk_agent_app/frontend/chat.html`."""
    return HTMLResponse(content=FRONTEND_CHAT_HTML_PATH.read_text(encoding="utf-8"))


@app.get("/guide", response_class=HTMLResponse, include_in_schema=False)
async def guide_ui() -> HTMLResponse:
    """Serves the SostaApp Architecture & Features Documentation page from `adk_agent_app/frontend/guide.html`."""
    return HTMLResponse(content=FRONTEND_GUIDE_HTML_PATH.read_text(encoding="utf-8"))



@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Liveness and persistence configuration check."""
    return {
        "status": "ok",
        "app_name": APP_NAME,
        "project_id": PROJECT_ID,
        "session_db": FIRESTORE_SESSION_DB,
        "session_service": type(sosta_runner.session_service).__name__,
        "memory_service": type(sosta_runner.memory_service).__name__,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """Executes one conversational turn using the persistent ADK `Runner` (JSON POST)."""
    should_save_memory = req.save_to_memory or bool(req.persist_memory)
    result = await execute_turn(
        runner=sosta_runner,
        user_id=req.user_id,
        session_id=req.session_id,
        message_text=req.message,
        save_to_memory=should_save_memory,
    )
    return ChatResponse(
        session_id=result["session_id"],
        user_id=result["user_id"],
        author=result["author"],
        response=result["response"],
        tool_calls=result["tool_calls"],
        session_state=result["session_state"],
    )


@app.get("/sessions/{user_id}/{session_id}")
async def inspect_session(user_id: str, session_id: str) -> Dict[str, Any]:
    """Retrieves the persisted Firestore session state, event count, and message history."""
    session = await sosta_runner.session_service.get_session(
        app_name=sosta_runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found for user '{user_id}'.",
        )
    messages: List[Dict[str, str]] = []
    for ev in session.events:
        if ev.content and ev.content.parts:
            texts = [
                p.text for p in ev.content.parts if hasattr(p, "text") and p.text
            ]
            if texts:
                messages.append(
                    {
                        "role": "user" if ev.author == "user" else "model",
                        "author": ev.author or "agent",
                        "text": "\n".join(texts),
                    }
                )
    return {
        "session_id": session.id,
        "user_id": session.user_id,
        "app_name": session.app_name,
        "state": session.state,
        "events_count": len(session.events),
        "last_update_time": session.last_update_time,
        "messages": messages,
    }


@app.delete("/sessions/{user_id}/{session_id}")
async def delete_session_endpoint(user_id: str, session_id: str) -> Dict[str, str]:
    """Purges a persisted session and its events subcollection from Firestore."""
    await sosta_runner.session_service.delete_session(
        app_name=sosta_runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    return {
        "status": "deleted",
        "user_id": user_id,
        "session_id": session_id,
    }
