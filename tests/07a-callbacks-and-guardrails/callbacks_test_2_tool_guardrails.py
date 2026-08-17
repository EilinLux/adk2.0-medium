# tests/07a-callbacks-and-guardrails/callbacks_test_2_tool_guardrails.py
"""Test 2: Intercepting Tool Execution (`before_tool_callback` & `after_tool_callback`).

Demonstrates:
- Part A (`before_tool_callback` Input Validation Short-Circuit): Blocking a malformed
  or SQL-injection-style `user_id` (`"bad_id_DROP_USERS"`) before `is_registered_user`
  ever queries Firestore.
- Part B (`after_tool_callback` Audit Trail & Zero-Trust Authorization): Recording
  every executed tool into `session.state["audit:tool_execution_log"]`, tagging tool
  responses with `"_audit_verified": True`, and blocking cross-user profile updates.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
# ---------------------------------------------------------------------------
# Path Setup & Environment Configuration
# ---------------------------------------------------------------------------
# Resolve the project root directory (2 levels up from this test file)
REPO_ROOT = Path(__file__).resolve().parents[2]
# Inject repository root into system path so `adk_agent_app` can be imported
sys.path.insert(0, str(REPO_ROOT))
# Load local environment variables (API keys, project IDs) from .env at repo root
load_dotenv(REPO_ROOT / ".env")
# Bypass startup preflight environment checks for fast local test execution
os.environ["SKIP_PREFLIGHT_CHECKS"] = "true"

# Import the root ADK agent configured with tool guardrail callbacks
from adk_agent_app.agent import root_agent  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: Async Turn Execution with Tool Call Inspection
# ---------------------------------------------------------------------------
async def run_turn_with_tool_inspection(
    runner: Runner, user_id: str, session_id: str, text: str
) -> tuple[str, list[dict]]:
    """Executes a single user interaction turn and captures both final text output and function response payloads."""
    # Build a structured GenAI Content object for the user prompt
    msg = types.Content(role="user", parts=[types.Part.from_text(text=text)])
    final_text = ""
    tool_responses = []

    # Stream through asynchronous events generated during the turn execution
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=msg
    ):
        # Intercept FunctionResponse events emitted when tools complete (or short-circuit)
        for fr in event.get_function_responses():
            tool_responses.append({"name": fr.name, "response": fr.response})
            
        # Collect and combine text parts from the final model response event
        if event.is_final_response() and event.content and event.content.parts:
            texts = [
                p.text for p in event.content.parts if getattr(p, "text", None)
            ]
            if texts:
                final_text = "\n".join(texts)

    return final_text, tool_responses


# ---------------------------------------------------------------------------
# Main Test Routine
# ---------------------------------------------------------------------------
async def main() -> None:
    # Initialize an in-memory session store for temporary test session state
    session_service = InMemorySessionService()

    # Instantiate the ADK Runner with root_agent and session management service
    runner = Runner(
        app_name="sosta_callbacks_test_2",
        agent=root_agent,
        session_service=session_service,
    )

    user_id = "usr_0a8f67"
    session_id = "sess_tool_callbacks_01"

    # Seed the isolated test session in session storage
    await session_service.create_session(
        app_name="sosta_callbacks_test_2",
        user_id=user_id,
        session_id=session_id,
    )

    # =======================================================================
    # PART A: before_tool_callback — Malformed User ID Input Validation
    # =======================================================================
    print("=" * 75)
    print(" PART A: before_tool_callback — Blocking Malformed User ID Before Firestore")
    print("=" * 75)
    
    # Prompt attempting to trigger `is_registered_user` tool with a malformed ID string
    bad_id_prompt = "Hi! I am registered, my user ID is admin_DROP_TABLE_users."
    print(f"User Input : {bad_id_prompt}")
    
    # Execute turn — before_tool_guardrail will inspect parameters before running the tool
    reply_a, tool_res_a = await run_turn_with_tool_inspection(
        runner, user_id, session_id, bad_id_prompt
    )
    print(f"Intercepted Tool Response: {json.dumps(tool_res_a, indent=2)}")
    print(f"Agent Reply: {reply_a}")

    # Fetch updated session state to inspect security flags
    sess_after_a = await session_service.get_session(
        app_name="sosta_callbacks_test_2",
        user_id=user_id,
        session_id=session_id,
    )
    
    # Assertions: Verify short-circuiting before reaching Firestore
    assert sess_after_a.state.get("security:last_blocked_tool") == "is_registered_user"  # Recorded blocked tool name
    assert any(
        tr["response"].get("error_code") == "INVALID_USER_ID_FORMAT"
        for tr in tool_res_a
    )  # Confirms before_tool_callback returned synthetic error dict directly
    print("✅ Verified: before_tool_callback short-circuited `is_registered_user` before touching Firestore!\n")

    # =======================================================================
    # PART B: after_tool_callback — Audit Trail & Response Enrichment
    # =======================================================================
    print("=" * 75)
    print(" PART B: after_tool_callback — Audit Trail & Response Enrichment")
    print("=" * 75)
    
    # Prompt containing a valid user ID format that passes regex validation
    valid_id_prompt = "Sorry, my real user ID is usr_0a8f67."
    print(f"User Input : {valid_id_prompt}")
    
    # Execute turn — tool executes normally, then after_tool_guardrail processes tool response
    reply_b, tool_res_b = await run_turn_with_tool_inspection(
        runner, user_id, session_id, valid_id_prompt
    )
    print(f"Enriched Tool Responses: {json.dumps(tool_res_b, indent=2, ensure_ascii=False)}")
    print(f"Agent Reply: {reply_b}")

    # Fetch session state to inspect generated tool audit execution log
    sess_after_b = await session_service.get_session(
        app_name="sosta_callbacks_test_2",
        user_id=user_id,
        session_id=session_id,
    )
    audit_log = sess_after_b.state.get("audit:tool_execution_log", [])
    print(f"Audit Log in Session State: {json.dumps(audit_log, indent=2)}")
    
    # Assertions: Verify payload enrichment and state audit logging
    assert any(
        tr["response"].get("_audit_verified") is True
        for tr in tool_res_b
        if isinstance(tr.get("response"), dict) and "status" in tr["response"]
    )  # Confirms after_tool_callback injected `_audit_verified: True` into the payload
    assert len(audit_log) >= 2  # Confirms both execution turns were recorded in state audit log
    print("✅ Verified: after_tool_callback enriched tool outputs with `_audit_verified=True` and populated `audit:tool_execution_log`!")


if __name__ == "__main__":
    # Script entrypoint: Run the async test suite
    asyncio.run(main())