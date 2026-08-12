# adk_agent_app/runner.py
import os
from typing import Any, Dict, List, Optional

from google.adk.agents.run_config import RunConfig
from google.adk.memory import BaseMemoryService
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.adk.sessions.session import Session
from google.genai import types

from .agent import root_agent
from .config import FIRESTORE_SESSION_DB, PROJECT_ID, logger
from .services import FirestoreSessionService, create_memory_service

APP_NAME = os.getenv("APP_NAME", "sosta_app")


def create_sosta_runner(
    session_service: Optional[BaseSessionService] = None,
    memory_service: Optional[BaseMemoryService] = None,
    use_vertex_memory_bank: bool = False,
) -> Runner:
    """Builds the production ADK `Runner` for SostaApp.

    Wires together:
    - `agent`: The root `Gatekeeper` hierarchy (`Gatekeeper`, `Registratore`, `Cameriere` -> A2A `Suggeritore`).
    - `session_service`: `FirestoreSessionService` backed by `adk-agent-dev-session-memory-fs`.
    - `memory_service`: `FirestoreMemoryService` (or `VertexAiMemoryBankService`) for cross-session recall.
    - `artifact_service`: Left as `None` because SostaApp's static Product Specification PDFs are
      indexed globally in Vertex AI RAG (`05c`), and the conversation produces text itineraries
      rather than per-session binary files.
    """
    active_session_service = session_service or FirestoreSessionService(
        project=PROJECT_ID,
        database=FIRESTORE_SESSION_DB,
    )
    active_memory_service = memory_service or create_memory_service(
        use_vertex_memory_bank=use_vertex_memory_bank
    )

    return Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=active_session_service,
        memory_service=active_memory_service,
        artifact_service=None,
    )


async def ensure_session(
    runner: Runner,
    user_id: str,
    session_id: str,
    initial_state: Optional[Dict[str, Any]] = None,
) -> Session:
    """Retrieves an existing session from `runner.session_service` or creates a new one."""
    existing = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if existing is not None:
        return existing

    return await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
        state=initial_state or {},
    )


async def execute_turn(
    runner: Runner,
    user_id: str,
    session_id: str,
    message_text: str,
    save_to_memory: bool = False,
    max_llm_calls: int = 15,
) -> Dict[str, Any]:
    """Executes a single conversational turn through the ADK `Runner` event loop.

    Args:
        runner: Initialized ADK `Runner`.
        user_id: Unique user identifier.
        session_id: Conversation session identifier.
        message_text: User's input message for this turn.
        save_to_memory: If True, ingests the updated session into `runner.memory_service` after the turn.
        max_llm_calls: Safety bound on LLM invocations per turn via `RunConfig`.

    Returns:
        Dict[str, Any]: Turn execution telemetry (`final_response`, `author`, `tool_calls`, `state`).
    """
    await ensure_session(runner=runner, user_id=user_id, session_id=session_id)

    user_msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message_text)],
    )
    run_config = RunConfig(max_llm_calls=max_llm_calls)

    tool_calls: List[Dict[str, Any]] = []
    state_deltas: List[Dict[str, Any]] = []
    final_text = ""
    final_author = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_msg,
        run_config=run_config,
    ):
        for fn_call in event.get_function_calls():
            tool_calls.append(
                {
                    "author": event.author,
                    "name": fn_call.name,
                    "args": dict(fn_call.args) if fn_call.args else {},
                }
            )

        if event.actions and event.actions.state_delta:
            state_deltas.append(dict(event.actions.state_delta))

        if event.is_final_response() and event.content and event.content.parts:
            text_parts = [
                part.text
                for part in event.content.parts
                if hasattr(part, "text") and part.text
            ]
            if text_parts:
                final_text = "\n".join(text_parts)
                final_author = event.author or ""

    updated_session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    if save_to_memory and updated_session and runner.memory_service:
        await runner.memory_service.add_session_to_memory(updated_session)
        logger.info(
            f"Session '{session_id}' committed to long-term MemoryService."
        )

    return {
        "session_id": session_id,
        "user_id": user_id,
        "author": final_author,
        "response": final_text,
        "tool_calls": tool_calls,
        "state_deltas": state_deltas,
        "session_state": updated_session.state if updated_session else {},
    }
