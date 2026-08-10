import asyncio
from typing import Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext

load_dotenv()


# 1. Pydantic Model for Structured Output Extraction
class PreferenceData(BaseModel):
    preferences: dict[str, Any] = Field(
        description="Key-value pairs of extracted user preferences (e.g., {'favorite_dish': 'Risotto Alla Milanese'})"
    )


# 2. Tool that populates Ephemeral ('temp:') State during execution
async def search_mock_restaurant_api(cuisine: str, tool_context: ToolContext) -> str:
    """Searches external API and stores raw payload in ephemeral 'temp:' state."""
    tool_context.session.state["temp:raw_api_payload"] = {
        "status_code": 200,
        "results_count": 3,
        "raw_response_bytes": "0x4150495f5241575f44415441"
    }
    return {
            "status": "success",
            "message": f"Found 3 restaurants for cuisine '{cuisine}'."
            }

# 3. Helper function to create the ADK Agents
def create_agents():
    gatekeeper_agent = Agent(
        name="gatekeeper_agent",
        model="gemini-2.5-flash",
        instruction="""
        You are a receptionist for sosta_app.
        Beta Recommendation Mode Status: {app:enable_beta_recommendations}
        
        Extract the user's dining preference from their message using the output schema.
        """,
        output_key="user_information",  # Plain Session Scope
        output_schema=PreferenceData
    )

    recommendation_agent = Agent(
        name="recommendation_agent",
        model="gemini-2.5-flash",
        instruction="""
        You are a dining concierge.
        
        USER PROFILE:
        - Language: {user:user_preferred_language}
        - Dietary: {user:dietary_restrictions}
        
        SESSION DATA:
        - Preference Extracted: {user_information?}
        - Special Requests: {special_requests?}
        
        Respond in the user's preferred language ({user:user_preferred_language}), acknowledge 
        their dietary restriction ({user:dietary_restrictions}), and call search_mock_restaurant_api to find options.
        """,
        tools=[search_mock_restaurant_api]
    )
    return gatekeeper_agent, recommendation_agent


async def main():
    session_service = InMemorySessionService()
    app_name = "sosta_app"
    gatekeeper_agent, recommendation_agent = create_agents()

    # Shared App-Scoped Configuration across all users
    global_app_config = {
        "app:enable_beta_recommendations": True,
        "app:system_version": "2.1.0"
    }

    print("==================================================================")
    print("TEST 1: ZELDA - SESSION 1 (Initial Preference Collection)")
    print("==================================================================")

    # 1. Initialize Zelda's persistent user profile and app config
    zelda_s1 = await session_service.create_session(
        app_name=app_name,
        user_id="user_zelda",
        session_id="zelda_session_1",
        state={
            **global_app_config,
            "user:user_preferred_language": "Italian",   # User Scope
            "user:dietary_restrictions": "Vegetarian",  # User Scope
            "current_subagent": "gatekeeper_agent",     # Session Scope
            "workflow_step": "preference_collection"    # Session Scope
        }
    )

    runner_gatekeeper = Runner(agent=gatekeeper_agent, app_name=app_name, session_service=session_service)
    
    # Zelda inputs her food craving in English; the agent parses it into session state
    msg_zelda_1 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="I am craving Risotto Alla Milanese tonight.")]
    )

    print("\n--- Gatekeeper Agent Parsing Zelda's Craving ---")
    for turn in runner_gatekeeper.run(user_id="user_zelda", session_id="zelda_session_1", new_message=msg_zelda_1):
        if turn.content and turn.content.parts:
            for part in turn.content.parts:
                if part.text:
                    print(f"Gatekeeper Response: {part.text}")

    # Check state after Gatekeeper runs
    updated_zelda_s1 = await session_service.get_session(app_name=app_name, user_id="user_zelda", session_id="zelda_session_1")
    print("\n[Zelda Session 1 State]:")
    print(f"- Session Scope ('user_information'): {updated_zelda_s1.state.get('user_information')}")
    print(f"- Ephemeral Scope ('temp:raw_api_payload'): {updated_zelda_s1.state.get('temp:raw_api_payload')} (Expected: None)")

    # 2. Run Recommendation Agent for Zelda (Triggers Tool + Ephemeral Temp State)
    runner_recommendation = Runner(agent=recommendation_agent, app_name=app_name, session_service=session_service)
    
    msg_zelda_2 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Please find me a place to eat.")]
    )

    print("\n--- Recommendation Agent Running for Zelda (Responds in Italian) ---")
    for turn in runner_recommendation.run(user_id="user_zelda", session_id="zelda_session_1", new_message=msg_zelda_2):
        if turn.content and turn.content.parts:
            for part in turn.content.parts:
                if part.text:
                    print(f"Agent Output: {part.text}")

    print("\n==================================================================")
    print("TEST 2: MARIO - USER ISOLATION & DIFFERENT LANGUAGE (English / Gluten-Free)")
    print("==================================================================")

    mario_s1 = await session_service.create_session(
        app_name=app_name,
        user_id="user_mario",
        session_id="mario_session_1",
        state={
            **global_app_config,
            "user:user_preferred_language": "English",    # User Scope (English)
            "user:dietary_restrictions": "Gluten-Free",  # User Scope (Gluten-Free)
            "current_subagent": "gatekeeper_agent",      # Session Scope
        }
    )

    # Pre-populate Mario's session preference directly to test subagent response
    mario_s1.state["user_information"] = {"preferences": {"favorite_dish": "Gluten-Free Pasta"}}

    msg_mario = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Suggest a good restaurant for me.")]
    )

    print("\n--- Recommendation Agent Running for Mario (Responds in English) ---")
    for turn in runner_recommendation.run(user_id="user_mario", session_id="mario_session_1", new_message=msg_mario):
        if turn.content and turn.content.parts:
            for part in turn.content.parts:
                if part.text:
                    print(f"Agent Output: {part.text}")

    print("\n==================================================================")
    print("TEST 3: ZELDA - SESSION 2 (Persistence Verification Across Sessions)")
    print("==================================================================")

    # Zelda opens a brand new chat session (`zelda_session_2`)
    # User-scoped keys persist, but session keys (`user_information`, `workflow_step`) reset!
    zelda_s2 = await session_service.create_session(
        app_name=app_name,
        user_id="user_zelda",
        session_id="zelda_session_2",
        state={
            **global_app_config,
            "user:user_preferred_language": "Italian",  # Persisted from DB/Profile
            "user:dietary_restrictions": "Vegetarian", # Persisted from DB/Profile
            "current_subagent": "gatekeeper_agent",     # Reset for new session
        }
    )

    print("\n--- Verifying Zelda's State in New Session 2 ---")
    print(f"1. User Language ('user:'):     {zelda_s2.state.get('user:user_preferred_language')} (Persisted across sessions)")
    print(f"2. Dietary Needs ('user:'):      {zelda_s2.state.get('user:dietary_restrictions')} (Persisted across sessions)")
    print(f"3. App Beta Flag ('app:'):       {zelda_s2.state.get('app:enable_beta_recommendations')} (Shared app-wide)")
    print(f"4. Old Dish ('user_information'): {zelda_s2.state.get('user_information')} (Expected: None - Reset for Session 2)")
    print(f"5. Temp Data ('temp:'):          {zelda_s2.state.get('temp:raw_api_payload')} (Expected: None - Cleared after turn)")


if __name__ == "__main__":
    asyncio.run(main())