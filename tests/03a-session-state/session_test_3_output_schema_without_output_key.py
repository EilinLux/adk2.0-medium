import asyncio
from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from pydantic import BaseModel, Field
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext

import os

# Clear Vertex AI routing environment variables
os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)
os.environ.pop("GCP_PROJECT", None)
os.environ.pop("GOOGLE_CLOUD_PROJECT", None)

# Set your standard AI Studio key
from dotenv import load_dotenv
load_dotenv()

class PopulateStateInput(BaseModel):
    key: str = Field(
        description="The state variable name extracted from the user input (e.g., 'favorite_city', 'user_age', 'preferred_theme')."
    )
    value: str = Field(
        description="The value extracted from the user input to assign to the key."
    )

class PopulateStateInput(BaseModel):
    preference: str = Field(
        description="The state variable name extracted from the user input (e.g., 'favorite_city', 'user_age', 'preferred_theme')."
    )
    value: str = Field(
        description="The value extracted from the user input to assign to the key."
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
        #output_key="preferences",
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