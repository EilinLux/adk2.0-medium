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
async def search_mock_restaurant_api(cuisine: str, tool_context: ToolContext) -> dict[str, Any]:
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
        output_key="user_information",  # Unprefixed: Session Scope
        output_schema=PreferenceData
    )

    recommendation_agent = Agent(
        name="recommendation_agent",
        model="gemini-2.5-flash",
        instruction="""
        You are a dining concierge.
        
        USER PROFILE:
- Language: 
{user:user_preferred_language}
- Dietary: 
{user:dietary_restrictions}
        
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

    # Setup Session 1 for Zelda
    await session_service.create_session(
        app_name=app_name,
        user_id="user_zelda",
        session_id="zelda_session_1",
        state={
            **global_app_config,
            "user:user_preferred_language": "Italian",   # User Scope
            "user:dietary_restrictions": "Vegetarian",  # User Scope
            "current_subagent": "gatekeeper_agent",     # Session Scope (Unprefixed)
            "workflow_step": "preference_collection"    # Session Scope (Unprefixed)
        }
    )

    runner_gatekeeper = Runner(agent=gatekeeper_agent, app_name=app_name, session_service=session_service)
    runner_recommendation = Runner(agent=recommendation_agent, app_name=app_name, session_service=session_service)

    # Turn 1: Gatekeeper Agent populates session-scoped `user_information`
    msg_zelda_1 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="I am craving Risotto Alla Milanese tonight.")]
    )
    for _ in runner_gatekeeper.run(user_id="user_zelda", session_id="zelda_session_1", new_message=msg_zelda_1):
        pass

    # Turn 2: Recommendation Agent runs tool which populates `temp:raw_api_payload`
    msg_zelda_2 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Please find me a place to eat.")]
    )
    for _ in runner_recommendation.run(user_id="user_zelda", session_id="zelda_session_1", new_message=msg_zelda_2):
        pass

    zelda_s1 = await session_service.get_session(app_name=app_name, user_id="user_zelda", session_id="zelda_session_1")

    # Setup Session for Mario (Different User)
    await session_service.create_session(
        app_name=app_name,
        user_id="user_mario",
        session_id="mario_session_1",
        state={
            "user:user_preferred_language": "English",
            "user:dietary_restrictions": "Gluten-Free",
            "current_subagent": "gatekeeper_agent",
        }
    )

    mario_s1 = await session_service.get_session(app_name=app_name, user_id="user_mario", session_id="mario_session_1")

    # Setup Session 2 for Zelda (New Session, Same User)
    zelda_s2 = await session_service.create_session(
        app_name=app_name,
        user_id="user_zelda",
        session_id="zelda_session_2",
        state={
            "current_subagent": "gatekeeper_agent",
        }
    )

    # =========================================================================
    # STATE BEHAVIOR DEMONSTRATION BY PREFIX
    # =========================================================================

    print("\n" + "=" * 70)
    print("1. UNPREFIXED SCOPE (Session-Bound State)")
    print("=" * 70)
    print("Behavior: Lives ONLY for the duration of a single session.")
    print("          Resets when opening a new session; isolated between users.")
    print(f"  - Zelda Session 1 ('user_information'): {zelda_s1.state.get('user_information')}")
    print(f"  - Mario Session 1 ('user_information'): {mario_s1.state.get('user_information')} (Isolated from Zelda)")
    print(f"  - Zelda Session 2 ('user_information'): {zelda_s2.state.get('user_information')} (RESET: Does not persist across sessions)")

    print("\n" + "=" * 70)
    print("2. 'temp:' PREFIX (Ephemeral Scope)")
    print("=" * 70)
    print("Behavior: Ephemeral state held in memory during turn execution.")
    print("          Automatically purged/omitted once session state is persisted.")
    print(f"  - Zelda Session 1 ('temp:raw_api_payload'): {zelda_s1.state.get('temp:raw_api_payload')} (Purged after turn)")
    print(f"  - Zelda Session 2 ('temp:raw_api_payload'): {zelda_s2.state.get('temp:raw_api_payload')} (None)")

    print("\n" + "=" * 70)
    print("3. 'user:' PREFIX (User Scope)")
    print("=" * 70)
    print("Behavior: Persists across ALL sessions belonging to the SAME user_id EVEN WHEN NOT EXPLICITLY PASSED.")
    print("          Isolated across different users.")
    print(f"  - Zelda Session 1 ('user:user_preferred_language'): {zelda_s1.state.get('user:user_preferred_language')}")
    print(f"  - Zelda Session 2 ('user:user_preferred_language'): {zelda_s2.state.get('user:user_preferred_language')} (PERSISTED from Session 1)")
    print(f"  - Mario Session 1 ('user:user_preferred_language'): {mario_s1.state.get('user:user_preferred_language')} (Isolated per user)")

    print("\n" + "=" * 70)
    print("4. 'app:' PREFIX (Application Scope)")
    print("=" * 70)
    print("Behavior: Shared globally across ALL sessions and ALL users in the app EVEN WHEN NOT EXPLICITLY PASSED.")
    print(f"  - Zelda Session 1 ('app:enable_beta_recommendations'): {zelda_s1.state.get('app:enable_beta_recommendations')}")
    print(f"  - Mario Session 1 ('app:enable_beta_recommendations'): {mario_s1.state.get('app:enable_beta_recommendations')} (Shared)")
    print(f"  - Zelda Session 2 ('app:enable_beta_recommendations'): {zelda_s2.state.get('app:enable_beta_recommendations')} (Shared)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())