# tests/06a-runner-session-and-memory/runner_test_2_firestore_session_persistence.py
"""Test 2: Stateless Container Resilience with `FirestoreSessionService` (`adk-agent-dev-session-memory-fs`).

Demonstrates:
1. Container Instance #1 (`runner_1`): Starts a conversation in `SostaApp`, authenticates `usr_0a8f67`
   via `Gatekeeper`, transfers control to `Cameriere`, and hydrates `user:` state into
   Firestore (`adk-agent-dev-session-memory-fs`).
2. Simulated Container Crash / Eviction: `runner_1` is destroyed in memory (`del runner_1`).
3. Container Instance #2 (`runner_2`): A brand-new `Runner` process attaches to the same
   `session_id` in Firestore, automatically restores the active sub-agent (`Cameriere`) and
   hydrated `user:` profile state, and seamlessly continues the trip planning conversation!
"""

import asyncio
from pathlib import Path
import sys

# Ensure project root is on sys.path when invoked directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv

load_dotenv()

from adk_agent_app.runner import APP_NAME, create_sosta_runner, execute_turn


async def main() -> None:
    print("=" * 80)
    print(
        "TEST 2: CONTAINER CRASH & RESTART RESILIENCE WITH `FirestoreSessionService`"
    )
    print("=" * 80)

    user_id = "traveler_giulia_persist"
    session_id = "sosta_cloud_session_persist_01"

    # Clean up any leftover session from previous test runs
    cleanup_runner = create_sosta_runner()
    await cleanup_runner.session_service.delete_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    # =========================================================================
    # PHASE 1: Container Instance #1 (Login & Handoff to Cameriere)
    # =========================================================================
    print("\n--- [Container Instance #1] Starting `runner_1` ---")
    runner_1 = create_sosta_runner()

    turn_1 = await execute_turn(
        runner=runner_1,
        user_id=user_id,
        session_id=session_id,
        message_text="Hello! I am registered, my ID is usr_0a8f67",
    )
    print(f"[Turn 1 Author]: {turn_1['author']}")
    print(f"[Turn 1 Tool Calls]: {[t['name'] for t in turn_1['tool_calls']]}")
    print(f"[Turn 1 Response]:\n{turn_1['response']}\n")
    print(f"[Persisted Firestore Session State]:\n{turn_1['session_state']}\n")

    # Simulate Cloud Run container eviction / scale-to-zero
    print("💥 Simulating container restart: destroying `runner_1` in memory...")
    del runner_1

    # =========================================================================
    # PHASE 2: Container Instance #2 (Resuming Conversation from Firestore)
    # =========================================================================
    print("\n--- [Container Instance #2] Booting fresh `runner_2` ---")
    runner_2 = create_sosta_runner()

    restored_session = await runner_2.session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    print(
        f"✅ Restored Session '{restored_session.id}' from Firestore "
        f"({len(restored_session.events)} persisted events, user:name='{restored_session.state.get('user:name')}')"
    )

    turn_2 = await execute_turn(
        runner=runner_2,
        user_id=user_id,
        session_id=session_id,
        message_text="Italiano va bene! Viaggio da sola verso Roma.",
    )
    print(f"\n[Turn 2 Author (Resumed on `runner_2`)]: {turn_2['author']}")
    print(f"[Turn 2 Response]:\n{turn_2['response']}\n")

    # Clean up test session
    await runner_2.session_service.delete_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    print("🧹 Cleaned up test session from Firestore.")


if __name__ == "__main__":
    asyncio.run(main())
