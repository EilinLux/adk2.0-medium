# adk_agent_app/server.py
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .config import FIRESTORE_SESSION_DB, PROJECT_ID
from .runner import APP_NAME, create_sosta_runner, execute_turn

app = FastAPI(
    title="SostaApp Production Runner API",
    description="FastAPI wrapper around the ADK 2.0 Runner backed by FirestoreSessionService and FirestoreMemoryService.",
    version="6.1.0",
)

# Singleton production Runner instance
sosta_runner = create_sosta_runner()


class ChatRequest(BaseModel):
    user_id: str = Field(
        ...,
        description="Caller identifier (e.g., 'usr_0a8f67' or 'traveler_zelda').",
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


class ChatResponse(BaseModel):
    session_id: str
    user_id: str
    author: str
    response: str
    tool_calls: List[Dict[str, Any]]
    session_state: Dict[str, Any]


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
    """Executes one conversational turn using the persistent ADK `Runner`."""
    result = await execute_turn(
        runner=sosta_runner,
        user_id=req.user_id,
        session_id=req.session_id,
        message_text=req.message,
        save_to_memory=req.save_to_memory,
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
    """Retrieves the persisted Firestore session state and event count."""
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
    return {
        "session_id": session.id,
        "user_id": session.user_id,
        "app_name": session.app_name,
        "state": session.state,
        "events_count": len(session.events),
        "last_update_time": session.last_update_time,
    }
