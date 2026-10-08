# tests/06a-runner-session-and-memory/runner_test_3_cross_session_memory_in_runner.py
"""Test 3: Cross-Session Long-Term Recall with `FirestoreMemoryService` + `preload_memory`.

Demonstrates:
1. Session 1 (`session_trip_last_month`): Traveler logs in, chats with `Cameriere`, and mentions
   traveling with their golden retriever Max and loving the Vegan Rainbow Salad at Secchia Ovest.
   At the end of the turn, `save_to_memory=True` commits the session to `sosta_memories` in
   `adk-agent-dev-session-memory-fs`.
2. Session 2 (`session_trip_today`): Weeks later, in a brand-new `session_id`, the same user
   logs in and asks `Cameriere` if it remembers their dog's name and favorite stop from last month.
   Because `Cameriere` includes ADK's `preload_memory` tool and `Runner` is wired to
   `FirestoreMemoryService`, `Cameriere` automatically recalls both facts across sessions!
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
        "TEST 3: CROSS-SESSION LONG-TERM MEMORY RECALL IN `Runner` (`preload_memory`)"
    )
    print("=" * 80)

    user_id = "traveler_memory_demo"
    session_1_id = "sosta_session_last_month_01"
    session_2_id = "sosta_session_today_02"

    runner = create_sosta_runner()

    # Clean up any leftover sessions from previous runs
    await runner.session_service.delete_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_1_id
    )
    await runner.session_service.delete_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_2_id
    )

    # =========================================================================
    # SESSION 1: Last Month's Trip (Saved to Long-Term Memory)
    # =========================================================================
    print(f"\n🗓️ [SESSION 1: '{session_1_id}'] Logging in & sharing trip details...")
    await execute_turn(
        runner=runner,
        user_id=user_id,
        session_id=session_1_id,
        message_text="Hello! I am already registered, my user ID is usr_0a8f67",
    )

    s1_turn_2 = await execute_turn(
        runner=runner,
        user_id=user_id,
        session_id=session_1_id,
        message_text=(
            "Let's continue in English please! Just so you know for my trips, "
            "I am traveling with my golden retriever dog named Max, and my favorite "
            "stop on the highway is Secchia Ovest because of the Vegan Rainbow Salad. "
            "Today I am heading to Rome."
        ),
        save_to_memory=True,  # Commits Session 1 to FirestoreMemoryService (`sosta_memories`)
    )
    print(f"[Cameriere (Session 1)]:\n{s1_turn_2['response']}\n")

    # =========================================================================
    # SESSION 2: Brand-New Session Today (Recalling Memory via `preload_memory`)
    # =========================================================================
    print(
        f"\n🗓️ [SESSION 2: '{session_2_id}'] Starting a brand-new session weeks later..."
    )
    await execute_turn(
        runner=runner,
        user_id=user_id,
        session_id=session_2_id,
        message_text="Hello! I am registered, my ID is usr_0a8f67",
    )

    s2_turn_2 = await execute_turn(
        runner=runner,
        user_id=user_id,
        session_id=session_2_id,
        message_text=(
            "Let's speak in English. Before we plan today's trip to Bologna, "
            "do you remember from our previous conversation what my dog's name is "
            "and which highway stop was my favorite?"
        ),
    )
    print(f"[Cameriere (Session 2 — Recalled via `preload_memory`)]:\n{s2_turn_2['response']}\n")

    # Clean up test sessions
    await runner.session_service.delete_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_1_id
    )
    await runner.session_service.delete_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_2_id
    )
    print("🧹 Cleaned up test sessions from Firestore.")


if __name__ == "__main__":
    asyncio.run(main())
