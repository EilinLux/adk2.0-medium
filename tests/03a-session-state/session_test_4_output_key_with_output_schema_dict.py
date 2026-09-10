import asyncio
from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from pydantic import BaseModel, Field
from google.adk.sessions import InMemorySessionService


# Set your standard AI Studio key
from dotenv import load_dotenv
load_dotenv()


from typing import Any
from pydantic import BaseModel, Field

class PopulateStateInput(BaseModel):
    preferences: dict[str, Any] = Field(
        description=(
            "A dictionary of state variables extracted from user input. "
            "Keys should be descriptive state variable names (e.g., 'favorite_dish', 'favorite_city', 'user_age'), "
            "and values should be the corresponding user preferences. for example: "
            "{'favorite_dish': 'Risotto Alla Milanese', 'favorite_city': 'Milan', 'preferred_theme': 'dark'} "
        ),

    )
    
async def main():
    # 1. Define the ADK Agent
    gatekeeper_agent = Agent(
        name="gatekeeper_agent",
        model="gemini-2.5-flash",
        instruction="""
        You are a helpful assistant for sosta_app. Whenever a user 
        provides personal details or preference information,
        save it into the session state as preference_xxx : preference_value.""",
        output_key="user_information",
        output_schema=PopulateStateInput,
    )

    # 2. Setup Session Service & Populate Initial Session Data
    session_service = InMemorySessionService()

    app_name = "sosta_app"
    user_id = "user_4567"
    session_id = "s_8f9a2b1c-9012"

    # Create the session with your initial state
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={
            "user_preferred_language": "Italian",
            "registered_user": True,
            "current_subagent": "gatekeeper_agent",
        }
    )

    # 3. Print the Initial State
    print("=== INITIAL SESSION STATE ===")
    print(session.state)
    print("=============================\n")

    # 4. Initialize Runner and Execute a Query
    runner = Runner(
        agent=gatekeeper_agent,
        app_name=app_name,
        session_service=session_service
    )

    # Unstructured input: The LLM will parse "favorite dish" -> key, "Risotto" -> value
    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text="My favorite dish is Risotto Alla Milanese.")]
    )   
    print("Sending message to agent...")
    for turn in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message
    ):
        if turn.content and turn.content.parts:
            for part in turn.content.parts:
                if part.text:
                    print(f"Agent Response: {part.text}")

    # 5. Fetch and Print the State After Execution
    updated_session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    print("\n=== UPDATED SESSION STATE ===")
    print(updated_session.state)
    print("=============================")


if __name__ == "__main__":
    asyncio.run(main())