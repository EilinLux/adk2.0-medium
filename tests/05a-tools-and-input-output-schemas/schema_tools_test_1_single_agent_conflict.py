# tests/05a-tools-and-input-output-schemas/schema_tools_test_1_single_agent_conflict.py
"""
Section 06 Test 1 — The Anti-Pattern: Combining `tools` + `output_schema` on a Conversational Tool Agent.

Demonstrates what happens when you attach `output_schema=RegistrationSummaryOutput` directly
onto a conversational tool-calling agent (`Registratore`) alongside `tools=[save_new_user_tool]`:
1. In a multi-turn onboarding flow (where the user hasn't provided all 5 fields yet), forcing
   `output_schema` on the tool agent either forces the LLM to emit premature/hallucinated JSON
   instead of asking follow-up questions, OR raises a Pydantic `ValidationError` when the agent
   replies in natural language.
2. In ADK 2.0, `output_schema` is enforced on EVERY final turn response of that agent via
   `validate_schema(self.output_schema, result)`.
"""
import asyncio
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path when running the script directly
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from adk_agent_app.schemas.user_schemas import RegistrationSummaryOutput
from adk_agent_app.tools.registratore_agent_tools import save_new_user_tool

load_dotenv()


async def main():
    print("=" * 75)
    print("TEST 1 (ANTI-PATTERN): Conversational Tool Agent with `tools` + `output_schema`")
    print("=" * 75)

    # Anti-pattern: Attaching `output_schema=RegistrationSummaryOutput` directly to Registratore
    conflicted_registratore = Agent(
        name="ConflictedRegistratore",
        model="gemini-2.5-flash",
        description="Attempts to collect profile data, call save_new_user, AND enforce output_schema.",
        instruction="""
        You are the registration assistant for Sosta.
        Collect the 5 required fields (full_name, email, preferred_language, culinary_preferences, vehicle_type).
        Do NOT invent missing values—ask the user if anything is missing.
        Once all 5 fields are collected, call `save_new_user`.
        """,
        tools=[save_new_user_tool],
        output_schema=RegistrationSummaryOutput,  # ❌ Forces JSON schema on EVERY turn!
        output_key="structured_registration_summary",
    )

    session_service = InMemorySessionService()
    app_name = "sosta_schema_test"
    user_id = "test_user_conflict"
    session_id = "session_conflict_01"

    await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    runner = Runner(
        agent=conflicted_registratore,
        app_name=app_name,
        session_service=session_service,
    )

    # User only gives their name on Turn 1 (missing email, language, diet, vehicle)
    user_message = types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text="Hi, I'd like to register! My name is Zelda Ailine Luconi."
            )
        ],
    )

    print("\n[User -> Turn 1]: Hi, I'd like to register! My name is Zelda Ailine Luconi.")
    print("(Notice that email, language, culinary preferences, and vehicle are still missing!)\n")

    try:
        for event in runner.run(
            user_id=user_id, session_id=session_id, new_message=user_message
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        print(f"  🔧 [Tool Call] {part.function_call.name}({part.function_call.args})")
                    if part.text:
                        print(f"  💬 [Agent Output] {part.text}")

        updated_session = await session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        print("\n=== SESSION STATE AFTER TURN 1 ===")
        print(json.dumps(updated_session.state, indent=2))
        print(
            "\n⚠️ Notice the problem: Instead of asking a natural follow-up question for the "
            "missing email/vehicle, `output_schema` forced the agent to emit a premature "
            "`RegistrationSummaryOutput` JSON object with fabricated/placeholder values "
            "before `save_new_user` was ever called!"
        )

    except Exception as exc:
        print(f"\n❌ Schema / Tool Conflict Raised: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
