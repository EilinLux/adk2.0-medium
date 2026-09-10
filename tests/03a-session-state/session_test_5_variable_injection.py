import asyncio
from typing import Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

load_dotenv()


class PopulateStateInput(BaseModel):
    preferences: dict[str, Any] = Field(
        description=(
            "A dictionary of state variables extracted from user input. "
            "Keys should be descriptive state variable names (e.g., 'favorite_dish', 'favorite_city'). "
            "Example: {'favorite_dish': 'Risotto Alla Milanese'}"
        ),
    )


async def main():
    # -------------------------------------------------------------------------
    # AGENT 1: Gatekeeper Agent
    # Extracts preference info and writes to session state under "user_information"
    # -------------------------------------------------------------------------
    gatekeeper_agent = Agent(
        name="gatekeeper_agent",
        model="gemini-2.5-flash",
        instruction="""
        You are a helpful assistant for sosta_app. Whenever a user 
        provides personal details or preference information,
        save it using the output schema.
        """,
        output_key="user_information",
        output_schema=PopulateStateInput,
    )

    # -------------------------------------------------------------------------
    # AGENT 2: Recommendation Subagent
    # Demonstrates the 3 {variable} injection rules in its instructions:
    # 1. Plain Key: {user_information} -> Reads session-scoped output from Agent 1
    # 2. Prefixed Key: {user:user_preferred_language} -> Reads user-scoped state
    # 3. Optional Key: {special_notes?} -> Injects empty string if key is absent
    # -------------------------------------------------------------------------
    recommendation_agent = Agent(
        name="recommendation_agent",
        model="gemini-2.5-flash",
        instruction="""
        You are a personal concierge for sosta_app.
        
        CONTEXT:
        - Language: {user:user_preferred_language}
        - User Info: {user_information}
        - Notes: {special_notes?}
        
        Using the language preference, greet the user in their language and 
        suggest a drink or restaurant pairing for their extracted favorite dish.
        """,
    )

    # Setup Session Service
    session_service = InMemorySessionService()
    app_name = "sosta_app"
    user_id = "user_4567"
    session_id = "s_8f9a2b1c-9012"

    # Create session with initial user-scoped language preference
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={
            "user:user_preferred_language": "Italian",
            "registered_user": True,
        }
    )

    print("=== 1. INITIAL SESSION STATE ===")
    print(session.state)
    print("================================\n")

    # -------------------------------------------------------------------------
    # STEP 1: Run Gatekeeper Agent to parse user input and save state
    # -------------------------------------------------------------------------
    runner = Runner(
        agent=gatekeeper_agent,
        app_name=app_name,
        session_service=session_service
    )

    user_message_1 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="My favorite dish is Risotto Alla Milanese.")]
    )   

    print("--- STEP 1: Running gatekeeper_agent ---")
    for turn in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message_1
    ):
        if turn.content and turn.content.parts:
            for part in turn.content.parts:
                if part.text:
                    print(f"Gatekeeper Response: {part.text}")

    # Inspect updated state after Agent 1 runs
    session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    print("\n=== 2. STATE AFTER GATEKEEPER AGENT ===")
    print(session.state)
    print("=======================================\n")

    # -------------------------------------------------------------------------
    # STEP 2: Run Recommendation Agent (Injects state into instructions)
    # -------------------------------------------------------------------------
    runner_subagent = Runner(
        agent=recommendation_agent,
        app_name=app_name,
        session_service=session_service
    )

    user_message_2 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Can you recommend a drink pairing for my food?")]
    )

    print("--- STEP 2: Running recommendation_agent ---")
    for turn in runner_subagent.run(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message_2
    ):
        if turn.content and turn.content.parts:
            for part in turn.content.parts:
                if part.text:
                    print(f"Recommendation Response: {part.text}")


if __name__ == "__main__":
    asyncio.run(main())