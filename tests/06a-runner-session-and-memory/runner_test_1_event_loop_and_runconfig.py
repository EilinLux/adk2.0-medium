# tests/06a-runner-session-and-memory/runner_test_1_event_loop_and_runconfig.py
"""Test 1: Anatomy of the ADK `Runner` Event Loop & `RunConfig`.

Demonstrates:
1. How `Runner` orchestrates `root_agent`, `SessionService`, and `MemoryService` outside `adk web`.
2. How `runner.run_async(..., run_config=RunConfig(...))` yields a stream of typed `Event` objects:
   - `[FunctionCall]`: Agent requesting a tool execution (`is_registered_user`, `transfer_to_agent`, `extract_user_profile`).
   - `[FunctionResponse]` + `[StateDelta]`: Tool output and mutations to `session.state` (`user:id`, `user:name`, `user:culinary_preferences`).
   - `[FinalResponse]`: The final conversational message returned to the user at the end of the turn.
"""

import asyncio
from pathlib import Path
import sys

# Ensure project root is on sys.path when invoked directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
from google.adk.agents.run_config import RunConfig
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

from adk_agent_app.agent import root_agent


async def run_and_inspect_turn(
    runner: Runner,
    user_id: str,
    session_id: str,
    user_text: str,
) -> None:
    print(f"\n[User]: {user_text}")
    print("-" * 80)

    msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_text)],
    )
    run_config = RunConfig(max_llm_calls=10)

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=msg,
        run_config=run_config,
    ):
        # 1. Inspect tool calls requested by the active agent
        for fn_call in event.get_function_calls():
            print(
                f"  ⚙️ [Event: FunctionCall]     author={event.author:<12} -> {fn_call.name}({dict(fn_call.args or {})})"
            )

        # 2. Inspect tool responses returned to the active agent
        for fn_resp in event.get_function_responses():
            print(
                f"  📦 [Event: FunctionResponse] author={event.author:<12} <- {fn_resp.name}"
            )

        # 3. Inspect state_delta mutations committed during this event
        if event.actions and event.actions.state_delta:
            print(
                f"  📝 [Event: StateDelta]       author={event.author:<12} delta={dict(event.actions.state_delta)}"
            )

        # 4. Inspect the final response emitted at the end of the turn
        if event.is_final_response() and event.content and event.content.parts:
            text = "\n".join(
                p.text for p in event.content.parts if hasattr(p, "text") and p.text
            )
            print(f"\n  🤖 [Event: FinalResponse]    author={event.author}:\n  {text}")


async def main() -> None:
    print("=" * 80)
    print("TEST 1: INSPECTING THE ADK `Runner` EVENT LOOP & `RunConfig`")
    print("=" * 80)

    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()
    runner = Runner(
        app_name="sosta_runner_demo",
        agent=root_agent,
        session_service=session_service,
        memory_service=memory_service,
    )

    user_id = "demo_traveler"
    session_id = "session_event_loop_01"
    await session_service.create_session(
        app_name="sosta_runner_demo",
        user_id=user_id,
        session_id=session_id,
    )

    # Turn 1: Greeting
    await run_and_inspect_turn(runner, user_id, session_id, "Hello!")

    # Turn 2: Existing User Login -> triggers Gatekeeper tool, handoff, and Cameriere hydration
    await run_and_inspect_turn(
        runner,
        user_id,
        session_id,
        "Yes, I am already registered. My user ID is usr_0a8f67",
    )


if __name__ == "__main__":
    asyncio.run(main())
