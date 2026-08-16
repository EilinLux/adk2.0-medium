# adk_agent_app/server.py
import json
import sys
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from google.adk.events.event import Event, EventActions
from google.adk.sessions.session import Session
from google.adk.version import __version__ as adk_version
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field

from .config import FIRESTORE_SESSION_DB, PROJECT_ID
from .runner import APP_NAME, DEFAULT_RUN_CONFIG, create_sosta_runner

FRONTEND_CHAT_HTML_PATH = Path(__file__).resolve().parent / "frontend" / "chat.html"
FRONTEND_GUIDE_HTML_PATH = Path(__file__).resolve().parent / "frontend" / "guide.html"

app = FastAPI(
    title="SostaApp Production Runner API (ADK Web Convention)",
    description=(
        "FastAPI server following the Google ADK Web / ApiServer endpoint convention "
        "(/dev-ui/, /run, /run_sse, /apps/{app_name}/users/{user_id}/sessions, "
        "/apps/{app_name}/users/{user_id}/memory), backed by FirestoreSessionService "
        "and FirestoreMemoryService."
    ),
    version="6.2.0",
)

# Singleton production Runner instance
sosta_runner = create_sosta_runner()


def _resolve_app_name(app_name: Optional[str]) -> str:
    """Normalizes 'adk_agent_app' or None to the Runner's canonical APP_NAME ('sosta_app')."""
    if not app_name or app_name in ("adk_agent_app", APP_NAME):
        return sosta_runner.app_name
    return app_name


class RunAgentRequest(BaseModel):
    """Standard ADK Web / ApiServer request payload for POST /run and POST /run_sse."""

    model_config = ConfigDict(populate_by_name=True)

    app_name: Optional[str] = Field(
        default=APP_NAME,
        alias="appName",
        description="Application name (defaults to 'sosta_app').",
    )
    user_id: str = Field(
        default="guest",
        alias="userId",
        description="Caller identifier (e.g., 'guest' for new users, or 'usr_0a8f67' for registered users).",
    )
    session_id: str = Field(
        default="prod_trip_001",
        alias="sessionId",
        description="Conversation session ID persisted in Firestore (`adk-agent-dev-session-memory-fs`).",
    )
    new_message: Optional[types.Content] = Field(
        default=None,
        alias="newMessage",
        description="ADK Content object containing role='user' and parts=[{'text': '...'}].",
    )
    user_content: Optional[str] = Field(
        default=None,
        description="Optional convenience text shorthand if new_message is omitted.",
    )
    streaming: bool = Field(
        default=False,
        description="Whether token-level streaming is enabled for /run_sse.",
    )
    state_delta: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="stateDelta",
        description="Optional state delta to merge before running the turn.",
    )
    invocation_id: Optional[str] = Field(
        default=None,
        alias="invocationId",
    )
    custom_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="customMetadata",
    )


class CreateSessionRequest(BaseModel):
    """Standard ADK Web request payload for POST /apps/{app_name}/users/{user_id}/sessions."""

    model_config = ConfigDict(populate_by_name=True)

    session_id: Optional[str] = Field(
        default=None,
        alias="sessionId",
        description="The ID of the session to create. If omitted, a UUID is generated.",
    )
    state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Initial state dictionary for the session.",
    )
    events: Optional[List[Event]] = Field(
        default=None,
        description="Optional initial events to append to the session.",
    )


class UpdateSessionRequest(BaseModel):
    """Standard ADK Web request payload for PATCH /apps/{app_name}/users/{user_id}/sessions/{session_id}."""

    model_config = ConfigDict(populate_by_name=True)

    state_delta: Dict[str, Any] = Field(
        ...,
        alias="stateDelta",
        description="State key-value changes to record on the session.",
    )


class UpdateMemoryRequest(BaseModel):
    """Standard ADK Web request payload for PATCH /apps/{app_name}/users/{user_id}/memory."""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(
        ...,
        alias="sessionId",
        description="The ID of the session to ingest into FirestoreMemoryService.",
    )


def _extract_content(req: RunAgentRequest) -> types.Content:
    if req.new_message is not None:
        if not req.new_message.role:
            req.new_message.role = "user"
        return req.new_message
    if req.user_content:
        return types.Content(
            role="user",
            parts=[types.Part.from_text(text=req.user_content)],
        )
    raise HTTPException(
        status_code=400,
        detail="new_message (or user_content) is required in RunAgentRequest.",
    )


async def _ensure_session(app_name: str, user_id: str, session_id: str) -> Session:
    session = await sosta_runner.session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        session = await sosta_runner.session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
    return session


def _inject_signed_in_user_hint(
    content: types.Content, user_id: str, session: Session
) -> types.Content:
    """If the user signed in via the UI dialog (user_id != 'guest') and is starting
    a brand-new session without repeating their ID in the message text, prepend a
    context tag so Gatekeeper can immediately verify `is_registered_user(user_id)`."""
    if (
        not user_id
        or user_id == "guest"
        or (session.events and len(session.events) > 0)
        or (session.state and session.state.get("verified_user_id"))
        or not content.parts
    ):
        return content

    first_text = getattr(content.parts[0], "text", None)
    if first_text and user_id not in first_text:
        new_parts = list(content.parts)
        new_parts[0] = types.Part.from_text(
            text=f"[Signed-in User ID: {user_id}] {first_text}"
        )
        return types.Content(role=content.role or "user", parts=new_parts)
    return content



async def _promote_registered_user_session_if_needed(
    app_name: str, original_user_id: str, session_id: str
) -> Optional[Session]:
    """If a 'guest' user registered or verified as 'usr_xxxxxx' during the turn,
    ensures the session is also accessible under that verified_user_id."""
    updated_session = await sosta_runner.session_service.get_session(
        app_name=app_name,
        user_id=original_user_id,
        session_id=session_id,
    )
    if updated_session and updated_session.state:
        verified_uid = updated_session.state.get("verified_user_id")
        if verified_uid and verified_uid != original_user_id:
            promoted = await sosta_runner.session_service.get_session(
                app_name=app_name,
                user_id=verified_uid,
                session_id=session_id,
            )
            if promoted is None:
                promoted = await sosta_runner.session_service.create_session(
                    app_name=app_name,
                    user_id=verified_uid,
                    session_id=session_id,
                    state=dict(updated_session.state),
                )
                for ev in updated_session.events:
                    await sosta_runner.session_service.append_event(promoted, ev)
            return promoted
    return updated_session


# ==============================================================================
# 1. ADK WEB UI & DOCUMENTATION ROUTES (/dev-ui/, /dev-ui/guide)
# ==============================================================================


@app.get("/", include_in_schema=False)
async def redirect_root_to_dev_ui() -> RedirectResponse:
    """Redirects '/' to '/dev-ui/' following the ADK Web convention."""
    return RedirectResponse(url="/dev-ui/")


@app.get("/dev-ui", include_in_schema=False)
async def redirect_dev_ui_slash() -> RedirectResponse:
    """Redirects '/dev-ui' to '/dev-ui/' following the ADK Web convention."""
    return RedirectResponse(url="/dev-ui/")


@app.get("/chat", include_in_schema=False)
async def redirect_chat_to_dev_ui() -> RedirectResponse:
    """Redirects '/chat' to '/dev-ui/'."""
    return RedirectResponse(url="/dev-ui/")


@app.get("/dev-ui/", response_class=HTMLResponse, include_in_schema=False)
async def dev_ui() -> HTMLResponse:
    """Serves the interactive SostaApp Production Runner Web UI from `adk_agent_app/frontend/chat.html`."""
    return HTMLResponse(content=FRONTEND_CHAT_HTML_PATH.read_text(encoding="utf-8"))


@app.get("/dev-ui/guide", response_class=HTMLResponse, include_in_schema=False)
@app.get("/guide", response_class=HTMLResponse, include_in_schema=False)
async def guide_ui() -> HTMLResponse:
    """Serves the SostaApp Architecture & Features Documentation page from `adk_agent_app/frontend/guide.html`."""
    return HTMLResponse(content=FRONTEND_GUIDE_HTML_PATH.read_text(encoding="utf-8"))


# ==============================================================================
# 2. DISCOVERY & HEALTH ENDPOINTS (/health, /version, /list-apps)
# ==============================================================================


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Liveness and Firestore persistence configuration check."""
    return {
        "status": "ok",
        "app_name": APP_NAME,
        "project_id": PROJECT_ID,
        "session_db": FIRESTORE_SESSION_DB,
        "session_service": type(sosta_runner.session_service).__name__,
        "memory_service": type(sosta_runner.memory_service).__name__,
    }


@app.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """Cloud Run liveness probe."""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check() -> Dict[str, str]:
    """Cloud Run startup / readiness probe."""
    return {"status": "ready"}



@app.get("/version")
async def version_info() -> Dict[str, str]:
    """ADK runtime and Python version metadata (ADK Web convention)."""
    return {
        "version": adk_version,
        "language": "python",
        "language_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


@app.get("/list-apps")
async def list_apps() -> List[str]:
    """Lists available ADK applications (ADK Web convention)."""
    return [APP_NAME, "adk_agent_app"]


# ==============================================================================
# 3. SESSION ENDPOINTS (/apps/{app_name}/users/{user_id}/sessions...)
# ==============================================================================


@app.get(
    "/apps/{app_name}/users/{user_id}/sessions",
    response_model_exclude_none=True,
)
async def list_sessions(app_name: str, user_id: str) -> List[Session]:
    """Lists all sessions for a user in FirestoreSessionService (ADK Web convention)."""
    resolved_app = _resolve_app_name(app_name)
    resp = await sosta_runner.session_service.list_sessions(
        app_name=resolved_app,
        user_id=user_id,
    )
    return list(resp.sessions)


@app.post(
    "/apps/{app_name}/users/{user_id}/sessions",
    response_model_exclude_none=True,
)
async def create_session(
    app_name: str,
    user_id: str,
    req: Optional[CreateSessionRequest] = Body(default=None),
) -> Session:
    """Creates a new session in FirestoreSessionService (ADK Web convention)."""
    resolved_app = _resolve_app_name(app_name)
    session = await sosta_runner.session_service.create_session(
        app_name=resolved_app,
        user_id=user_id,
        state=req.state if req else None,
        session_id=req.session_id if req else None,
    )
    if req and req.events:
        for ev in req.events:
            await sosta_runner.session_service.append_event(session=session, event=ev)
    return session


@app.post(
    "/apps/{app_name}/users/{user_id}/sessions/{session_id}",
    response_model_exclude_none=True,
)
async def create_session_with_id(
    app_name: str,
    user_id: str,
    session_id: str,
    state: Optional[Dict[str, Any]] = Body(default=None),
) -> Session:
    """Creates or returns a session with an explicit session_id (ADK Web convention)."""
    resolved_app = _resolve_app_name(app_name)
    return await sosta_runner.session_service.create_session(
        app_name=resolved_app,
        user_id=user_id,
        session_id=session_id,
        state=state,
    )


@app.get(
    "/apps/{app_name}/users/{user_id}/sessions/{session_id}",
    response_model_exclude_none=True,
)
async def get_session(
    app_name: str,
    user_id: str,
    session_id: str,
) -> Session:
    """Retrieves the persisted Firestore Session including state and events (ADK Web convention)."""
    resolved_app = _resolve_app_name(app_name)
    session = await sosta_runner.session_service.get_session(
        app_name=resolved_app,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found for user '{user_id}'.",
        )
    return session


@app.patch(
    "/apps/{app_name}/users/{user_id}/sessions/{session_id}",
    response_model_exclude_none=True,
)
async def update_session(
    app_name: str,
    user_id: str,
    session_id: str,
    req: UpdateSessionRequest,
) -> Session:
    """Updates session state via state_delta without running the agent (ADK Web convention)."""
    resolved_app = _resolve_app_name(app_name)
    session = await sosta_runner.session_service.get_session(
        app_name=resolved_app,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found for user '{user_id}'.",
        )
    state_update_event = Event(
        invocation_id="p-" + str(uuid.uuid4()),
        author="user",
        actions=EventActions(state_delta=req.state_delta),
    )
    await sosta_runner.session_service.append_event(
        session=session,
        event=state_update_event,
    )
    updated = await sosta_runner.session_service.get_session(
        app_name=resolved_app,
        user_id=user_id,
        session_id=session_id,
    )
    return updated or session


@app.delete("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def delete_session(
    app_name: str,
    user_id: str,
    session_id: str,
) -> Dict[str, str]:
    """Deletes a persisted session and its events subcollection from Firestore (ADK Web convention)."""
    resolved_app = _resolve_app_name(app_name)
    await sosta_runner.session_service.delete_session(
        app_name=resolved_app,
        user_id=user_id,
        session_id=session_id,
    )
    return {
        "status": "deleted",
        "app_name": resolved_app,
        "user_id": user_id,
        "session_id": session_id,
    }


# ==============================================================================
# 4. MEMORY ENDPOINT (/apps/{app_name}/users/{user_id}/memory)
# ==============================================================================


@app.patch("/apps/{app_name}/users/{user_id}/memory")
async def patch_memory(
    app_name: str,
    user_id: str,
    req: UpdateMemoryRequest,
) -> Dict[str, str]:
    """Commits all events from a given session to FirestoreMemoryService (ADK Web convention)."""
    resolved_app = _resolve_app_name(app_name)
    session = await sosta_runner.session_service.get_session(
        app_name=resolved_app,
        user_id=user_id,
        session_id=req.session_id,
    )
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{req.session_id}' not found for user '{user_id}'.",
        )
    await sosta_runner.memory_service.add_session_to_memory(session)
    return {
        "status": "committed_to_memory",
        "app_name": resolved_app,
        "user_id": session.user_id,
        "session_id": session.id,
    }


# ==============================================================================
# 5. AGENT EXECUTION ENDPOINTS (POST /run and POST /run_sse)
# ==============================================================================


@app.post("/run", response_model_exclude_none=True)
async def run_agent(req: RunAgentRequest) -> List[Event]:
    """Executes one conversational turn and returns the list of ADK Events (ADK Web convention)."""
    resolved_app = _resolve_app_name(req.app_name)
    content = _extract_content(req)
    session = await _ensure_session(
        app_name=resolved_app,
        user_id=req.user_id,
        session_id=req.session_id,
    )
    content = _inject_signed_in_user_hint(content, req.user_id, session)

    events: List[Event] = []
    async for event in sosta_runner.run_async(
        user_id=req.user_id,
        session_id=req.session_id,
        new_message=content,
        state_delta=req.state_delta,
        invocation_id=req.invocation_id,
        run_config=DEFAULT_RUN_CONFIG,
    ):
        events.append(event)

    await _promote_registered_user_session_if_needed(
        app_name=resolved_app,
        original_user_id=req.user_id,
        session_id=req.session_id,
    )
    return events


@app.post("/run_sse")
async def run_agent_sse(req: RunAgentRequest) -> StreamingResponse:
    """Executes one conversational turn and streams ADK Events over SSE (ADK Web convention)."""
    resolved_app = _resolve_app_name(req.app_name)
    content = _extract_content(req)
    session = await _ensure_session(
        app_name=resolved_app,
        user_id=req.user_id,
        session_id=req.session_id,
    )
    content = _inject_signed_in_user_hint(content, req.user_id, session)

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in sosta_runner.run_async(
                user_id=req.user_id,
                session_id=req.session_id,
                new_message=content,
                state_delta=req.state_delta,
                invocation_id=req.invocation_id,
                run_config=DEFAULT_RUN_CONFIG,
            ):
                sse_payload = event.model_dump_json(exclude_none=True, by_alias=True)
                yield f"data: {sse_payload}\n\n"
            await _promote_registered_user_session_if_needed(
                app_name=resolved_app,
                original_user_id=req.user_id,
                session_id=req.session_id,
            )
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
