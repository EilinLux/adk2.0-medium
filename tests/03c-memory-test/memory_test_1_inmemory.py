import asyncio
from typing import Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.adk.memory import InMemoryMemoryService
import warnings
load_dotenv()

# Suppress experimental warnings and deprecation notices
warnings.filterwarnings("ignore", message=".*JSON_SCHEMA_FOR_FUNC_DECL.*")
warnings.filterwarnings(
    "ignore", 
    category=FutureWarning, 
    module="google.adk.memory.vertex_ai_memory_bank_service"
)


# 1. Pydantic Model for Structured Output Extraction
class PreferenceData(BaseModel):
    preferences: dict[str, Any] = Field(
        description="Key-value pairs of extracted user preferences (e.g., {'culinary_preference': 'Salmon'})"
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
        "message": f"Found 3 restaurants for cuisine/ingredient '{cuisine}'."
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
        output_key="user_information",
        output_schema=PreferenceData
    )

    recommendation_agent = Agent(
        name="recommendation_agent",
        model="gemini-2.5-flash",
        instruction="""
        You are a dining concierge.
        
        USER PROFILE:
        - Language: {user:user_preferred_language}
        - Prior Context / Known Memories: {user:prior_context?}
        
        SESSION DATA:
        - Preference Extracted: {user_information?}
        
        Respond in the user's preferred language ({user:user_preferred_language}).
        Check past user preferences and memories (e.g., newly liked foods such as salmon) to suggest relevant options.
        Call search_mock_restaurant_api to find options if appropriate.
        """,
        tools=[search_mock_restaurant_api]
    )
    return gatekeeper_agent, recommendation_agent


async def main():
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()

    app_name = "sosta_app"
    gatekeeper_agent, recommendation_agent = create_agents()

    global_app_config = {
        "app:enable_beta_recommendations": True,
        "app:system_version": "2.1.0"
    }

    print("==================================================================")
    print("SESSION 1: Historical Interaction (3 Weeks Ago)")
    print("==================================================================")

    # 1. Initialize session for the past conversation
    zelda_s1 = await session_service.create_session(
        app_name=app_name,
        user_id="user_zelda",
        session_id="zelda_session_1",
        state={
            **global_app_config,
            "user:user_preferred_language": "English",
            "current_subagent": "gatekeeper_agent",
        }
    )

    # Simulate historical user message from 3 weeks ago
    historical_msg = types.Content(
        role="user",
        parts=[types.Part.from_text(
            text="I used to hate seafood, but last night I tried salmon in Seattle and loved it! Oh, and my dog Max loved the trip too."
        )]
    )

    runner_gatekeeper = Runner(agent=gatekeeper_agent, app_name=app_name, session_service=session_service)

    print("\n--- Processing Historical Statement ---")
    for turn in runner_gatekeeper.run(user_id="user_zelda", session_id="zelda_session_1", new_message=historical_msg):
        if turn.content and turn.content.parts:
            for part in turn.content.parts:
                if part.text:
                    print(f"Gatekeeper Parsed: {part.text}")

    # Commit historical conversation session to long-term memory
    updated_zelda_s1 = await session_service.get_session(app_name=app_name, user_id="user_zelda", session_id="zelda_session_1")
    await memory_service.add_session_to_memory(updated_zelda_s1)

    print("\n==================================================================")
    print("SESSION 2: Current Session Query ('What can I eat for dinner?')")
    print("==================================================================")

    # Search long-term memory for past food/culinary preferences
    results = await memory_service.search_memory(
        app_name=app_name,
        user_id="user_zelda",
        query="what food or culinary preferences does the user have?"
    )
    # To this:
    prior_context = "\n".join(
    [
        part.text
        for r in results.memories
        if r.content and r.content.parts
        for part in r.content.parts
        if part.text
    ]
    )
    # Create a fresh session representing today's conversation
    zelda_s2 = await session_service.create_session(
        app_name=app_name,
        user_id="user_zelda",
        session_id="zelda_session_2",
        state={
            **global_app_config,
            "user:user_preferred_language": "English",
            "user:prior_context": prior_context,
            "current_subagent": "recommendation_agent"
        }
    )

    runner_recommendation = Runner(agent=recommendation_agent, app_name=app_name, session_service=session_service)

    # User asks what to eat for dinner
    dinner_query = types.Content(
        role="user",
        parts=[types.Part.from_text(text="What can I eat for dinner?")]
    )

    print("\n--- Recommendation Agent Processing Query ---")
    for turn in runner_recommendation.run(user_id="user_zelda", session_id="zelda_session_2", new_message=dinner_query):
        if turn.content and turn.content.parts:
            for part in turn.content.parts:
                if part.text:
                    print(f"Agent Output: {part.text}")


if __name__ == "__main__":
    asyncio.run(main())