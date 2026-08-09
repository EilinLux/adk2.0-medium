"""
ADK 2.0 101 - Article 3b: Session Service Demo
----------------------------------------------
This script demonstrates the complete SessionService lifecycle in Google ADK:
1. Creating & Seeding sessions across state scopes (app:, user:, plain, temp:)
2. Writing to live session state inside custom tools using `ToolContext`
3. Dynamically injecting state variables into agent prompt templates
4. Updating state mid-pipeline via append_event with state_delta
5. Switching between InMemorySessionService and DatabaseSessionService (SQLite)
"""
from dotenv import load_dotenv
from google.genai import types
import asyncio
import os
from typing import Any, Dict
from pydantic import BaseModel, Field

from google.adk.agents import Agent
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.tools import ToolContext
 
 
load_dotenv()

# ============================================================================
# 1. Structured Schemas & Custom Tools
# ============================================================================

class PreferenceExtraction(BaseModel):
    favorite_dish: str = Field(
        description="The user's favorite dish or food preference extracted from text."
    )


async def search_restaurant_api(cuisine: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Mock external restaurant API tool.
    Demonstrates writing ephemeral execution metadata directly to `temp:` state
    using `ToolContext`.
    """
    # Write heavy or temporary execution data to temp: scope
    tool_context.session.state["temp:raw_api_payload"] = {
        "status_code": 200,
        "query_cuisine": cuisine,
        "results_count": 3,
        "raw_response_bytes": "0x4150495f5241575f44415441",
    }

    return {
        "status": "success",
        "message": f"Found 3 top-rated restaurants matching '{cuisine}'.",
    }


# ============================================================================
# 2. Agent Definitions & State Injection
# ============================================================================

gatekeeper_agent = Agent(
    name="gatekeeper_agent",
    model="gemini-2.5-flash",
    instruction="""
    You are a welcoming assistant for sosta_app. 
    Whenever a user mentions a food preference or favorite dish, 
    extract it cleanly using the response schema.
    """,
    output_key="user_information",
    output_schema=PreferenceExtraction,
)

concierge_agent = Agent(
    name="concierge_agent",
    model="gemini-2.5-flash",
    instruction="""
    You are a dining concierge for sosta_app.

    USER PROFILE:
    - Language: {user:user_preferred_language}
    - Dietary: {user:dietary_restrictions}

    SESSION CONTEXT:
    - Extracted Info: {user_information?}
    - Active Step: {workflow_step?}

    Respond in the user's preferred language ({user:user_preferred_language}), 
    acknowledge their dietary restriction ({user:dietary_restrictions}), 
    and use the 'search_restaurant_api' tool to find matching restaurants.
    """,
    tools=[search_restaurant_api],
)


# ============================================================================
# 3. Main Session Lifecycle Execution Loop
# ============================================================================

async def main():
    APP_NAME = "sosta_app"
    USER_ID = "user_zelda"
    SESSION_ID = "zelda_session_101"

    print("============================================================")
    print("🚀 1. INITIALIZING SESSION SERVICE & SEEDING STATE")
    print("============================================================")

    # Choose your backend (Uncomment DatabaseSessionService to test SQLite persistence)
    # session_service = InMemorySessionService()
    db_url = "sqlite+aiosqlite:///./sosta_sessions.db"
    session_service = DatabaseSessionService(db_url=db_url)

    global_app_config = {
        "app:enable_beta_recommendations": True,
        "app:system_version": "2.1.0",
    }

    # 1. CREATE & SEED SESSION
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state={
            **global_app_config,
            "user:user_preferred_language": "Italian",   # Permanent User Scope
            "user:dietary_restrictions": "Vegetarian",  # Permanent User Scope
            "current_subagent": "gatekeeper_agent",     # Session Scope
            "workflow_step": "preference_collection",   # Session Scope
        },
    )

    print(f"Created Session: {session.id} for User: {session.user_id}")
    print("Initial State:", session.state)

    print("\n============================================================")
    print("🔄 2. MID-PIPELINE STATE PATCH (append_event with state_delta)")
    print("============================================================")

    # 2. UPDATE SESSION STATE VIA EVENT DELTA
    event = Event(
        author="system",
        actions=EventActions(state_delta={"workflow_step": "concierge_recommendation"}),
    )
    await session_service.append_event(session=session, event=event)

    updated_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    print("Updated Workflow Step:", updated_session.state.get("workflow_step"))

    print("\n============================================================")
    print("🤖 3. EXECUTING AGENT TURN WITH TOOLCONTEXT & INJECTION")
    print("============================================================")

    # Initialize Runner with SessionService
    runner = Runner(
        agent=concierge_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )


    # Construct a valid Content object
    query_text = "Can you find a good place for dinner tonight?"
    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=query_text)]
    )

    # 2. Pass the Content object to run_async
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=user_message,  # Fixed: pass Content object, not str
    ):

        if event.is_final_response() and event.content:
            part = event.content.parts[0]
            if hasattr(part, "text") and part.text:
                print(f"Agent Response:\n{part.text}\n")

    print("============================================================")
    print("📖 4. READING FINAL STATE & INSPECTING SCOPES")
    print("============================================================")

    # 3. READ SESSION STATE POST-RUN
    final_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )

    print("Final State Keys & Values:")
    print(f"- User Language (user:): {final_session.state.get('user:user_preferred_language')}")
    print(f"- App Version (app:):   {final_session.state.get('app:system_version')}")
    print(f"- Workflow Step (plain): {final_session.state.get('workflow_step')}")
    print(f"- Ephemeral Payload (temp:): {final_session.state.get('temp:raw_api_payload')}")

    print("\n============================================================")
    print("🧹 5. EVICTING SESSION (DELETE)")
    print("============================================================")

    # 4. DELETE SESSION
    await session_service.delete_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    print(f"Session '{SESSION_ID}' successfully deleted from storage backend.")


if __name__ == "__main__":
    asyncio.run(main())