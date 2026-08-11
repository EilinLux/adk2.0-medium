# tests/05a-tools-and-input-output-schemas/schema_tools_test_2_two_agent_split.py
"""
Section 06 Test 2 — The Production Pattern: Two-Agent Split (`tools` -> `output_key` -> `output_schema`).

Demonstrates the clean Digital Assembly Line separation for SostaApp:
- Station 1 (Tool Agent): Calls `save_new_user_tool` freely with NO `output_schema`,
  saving its findings to `session.state["raw_registration_result"]` via `output_key`.
- Station 2 (Formatter Agent): Reads `{raw_registration_result}` from session state and
  enforces `output_schema=RegistrationSummaryOutput` with NO tools, saving the validated
  structured dictionary to `session.state["structured_registration_summary"]`.
"""
import asyncio
import json
import os
from pathlib import Path
import sys

# Ensure repository root is on sys.path when running the script directly
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from google.adk import Agent, Workflow
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from adk_agent_app.schemas.user_schemas import RegistrationSummaryOutput
from adk_agent_app.subagents.registratore_agent import registration_formatter_agent
from adk_agent_app.tools.registratore_agent_tools import save_new_user_tool

load_dotenv()
# Enable deterministic ID generation ('usr_7c0adf' for zelda.luconi@gmail.com)
os.environ["ADK_EVAL_MODE"] = "true"


async def main():
    print("=" * 70)
    print("TEST 2 (PRODUCTION PATTERN): Two-Agent Split (Tool Agent -> Formatter Agent)")
    print("=" * 70)

    # Station 1: Tool Agent (calls `save_new_user_tool` freely, no `output_schema`)
    station_1_tool_agent = Agent(
        name="RegistratoreToolStation",
        model="gemini-2.5-flash",
        description="Onboards a new user using save_new_user_tool and writes raw result to state.",
        instruction="""
        You are the registration assistant for Sosta.
        When the user provides their full name, email, preferred language, culinary preferences,
        and vehicle type, call `save_new_user` immediately.
        After `save_new_user` returns, summarize the registration outcome clearly including:
        - status ('success' or 'failed')
        - user_id
        - full_name
        - preferred_language
        - whether the profile was hydrated into session memory (True/False).
        """,
        tools=[save_new_user_tool],
        output_key="raw_registration_result",  # Writes natural text summary to session.state
    )

    # Station 2: Imported directly from `adk_agent_app.subagents.registratore_agent`
    # (`registration_formatter_agent`, which reads `{raw_registration_result}` and applies
    # `output_schema=RegistrationSummaryOutput` + `output_key="structured_registration_summary"`)
    onboarding_pipeline = Workflow(
        name="OnboardingTwoStationPipeline",
        edges=[
            ("START", station_1_tool_agent, registration_formatter_agent),
        ],
    )

    session_service = InMemorySessionService()
    app_name = "sosta_schema_test"
    user_id = "zelda_test_user"
    session_id = "session_two_station_01"

    await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    runner = Runner(
        agent=onboarding_pipeline,
        app_name=app_name,
        session_service=session_service,
    )

    user_message = types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text=(
                    "Please register me: My name is Zelda Ailine Luconi, my email is "
                    "zelda.luconi@gmail.com, my preferred language is Italian, my culinary "
                    "preferences are Vegan, and I drive an Electric vehicle."
                )
            )
        ],
    )

    print("\nSending onboarding request through the 2-Station Pipeline...\n")
    for event in runner.run(
        user_id=user_id, session_id=session_id, new_message=user_message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    print(
                        f"🔧 [{event.author} -> Tool Call] "
                        f"{part.function_call.name}({part.function_call.args})"
                    )
                if part.text:
                    print(f"💬 [{event.author} -> Output]\n{part.text}\n")

    # Fetch and inspect the resulting session state
    updated_session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    print("=" * 70)
    print("1. STATION 1 OUTPUT (`session.state['raw_registration_result']`):")
    print("=" * 70)
    print(updated_session.state.get("raw_registration_result"))

    print("\n" + "=" * 70)
    print("2. STATION 2 VALIDATED SCHEMA OUTPUT (`session.state['structured_registration_summary']`):")
    print("=" * 70)
    structured_summary = updated_session.state.get("structured_registration_summary")
    print(json.dumps(structured_summary, indent=2))

    # Validate that the dictionary in state conforms strictly to RegistrationSummaryOutput
    validated_model = RegistrationSummaryOutput.model_validate(structured_summary)
    print("\n✅ Pydantic Schema Validation Passed:", validated_model)


if __name__ == "__main__":
    asyncio.run(main())
