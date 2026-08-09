import asyncio
import os
import warnings
from typing import Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from google.genai import types
from google.genai.errors import ClientError
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.adk.memory import VertexAiMemoryBankService
from agentplatform import Client as agentplatform_client

# Suppress experimental warnings and deprecation notices
warnings.filterwarnings("ignore", message=".*JSON_SCHEMA_FOR_FUNC_DECL.*")
warnings.filterwarnings(
    "ignore", 
    category=FutureWarning, 
    module="google.adk.memory.vertex_ai_memory_bank_service"
)

load_dotenv()

# ============================================================================
# 1. Structured Schemas & Custom Tools
# ============================================================================

class PreferenceExtraction(BaseModel):
    favorite_dish: str = Field(
        description="The user's favorite dish, ingredient, or culinary preference."
    )

async def search_mock_restaurant_api(cuisine: str, tool_context: ToolContext) -> dict:
    """Mock API tool that records execution state in temp: scope."""
    tool_context.session.state["temp:raw_api_payload"] = {
        "status_code": 200,
        "query": cuisine
    }
    return {
        "status": "success",
        "message": f"Found 3 top-rated restaurants matching '{cuisine}'."
    }

def create_memory_bank_and_client():
    """Creates a Vertex AI Memory Bank and returns the client and agent engine ID."""
    client = agentplatform_client()
    
    memory_bank = client.agent_engines.create(
        config={
            "display_name": "sosta_app_memory_bank",
            "description": "Memory Bank for sosta_app dining preferences",
        }
    )
    
    agent_engine_id = memory_bank.api_resource.name.split("/")[-1]
    print("Full resource name:", memory_bank.api_resource.name)
    print("Numeric ID to use:", agent_engine_id)
    return client, memory_bank.api_resource.name, agent_engine_id


# ============================================================================
# 2. Define the Two Specialized Micro-Agents
# ============================================================================

# Agent 1: Extracts preferences into session.state under 'user_information'
gatekeeper_agent = Agent(
    name="gatekeeper_agent",
    model="gemini-2.5-flash",
    instruction="""
    You are the Gatekeeper for sosta_app.
    Extract the user's culinary preference or food discoveries from their message 
    and save it using the output schema.
    """,
    output_key="user_information",
    output_schema=PreferenceExtraction,
)

# Agent 2: Reads 'user_information' from session.state and executes search tool
recommendation_agent = Agent(
    name="recommendation_agent",
    model="gemini-2.5-flash",
    instruction="""
    You are a dining concierge for sosta_app.

    USER PROFILE:
    - Language: {user:user_preferred_language?}
    - Dietary: {user:dietary_restrictions?}

    SESSION CONTEXT:
    - Extracted Preference: {user_information?}

    INSTRUCTIONS:
    1. Check the Extracted Preference ({user_information?}) or memory history for preferred ingredients (e.g. salmon).
    2. Call `search_mock_restaurant_api` to search options for that ingredient/cuisine.
    3. Provide a friendly recommendation in the user's preferred language ({user:user_preferred_language?}).
    """,
    tools=[search_mock_restaurant_api]
)


# ============================================================================
# 3. Define Supervisor Agent & Single Runner
# ============================================================================

# Supervisor delegates turns to sub_agents based on task requirements
supervisor_agent = Agent(
    name="sosta_supervisor",
    model="gemini-2.5-flash",
    instruction="""
    You are the chief supervisor for Sosta App.
    - If the user is sharing a new food preference, discovery, or dietary habit, route to `gatekeeper_agent`.
    - If the user is asking for dinner, meal, or restaurant recommendations, route to `recommendation_agent`.
    """,
    sub_agents=[gatekeeper_agent, recommendation_agent]
)




async def main():
    APP_NAME = "sosta_app"
    USER_ID = "user_zelda"
    SESSION_ID = "zelda_session_101"

    session_service = InMemorySessionService()
    ap_client, full_resource_name, agent_engine_id = create_memory_bank_and_client()
    memory_service = VertexAiMemoryBankService(agent_engine_id=agent_engine_id)

    # ONE SINGLE RUNNER manages the supervisor and both sub-agents!
    runner = Runner(
        agent=supervisor_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service
    )

    global_app_config = {
        "app:enable_beta_recommendations": True,
        "app:system_version": "2.1.0"
    }
    # Create Session Thread
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state={
            "user:user_preferred_language": "English",
            "user:dietary_restrictions": "None"
        }
    )
# ============================================================================
# 3. Execution Across 2 Independent Sessions
# ============================================================================

async def main():
    APP_NAME = "sosta_app"
    USER_ID = "user_zelda"

    session_service = InMemorySessionService()
    
    memory_service = VertexAiMemoryBankService(
        agent_engine_id=create_memory_bank_and_client()[2]
    )

    # ------------------------------------------------------------------------
    # SESSION 1: 3 Weeks Ago (Session ID: zelda_session_101)
    # ------------------------------------------------------------------------
    print("==================================================================")
    print("🗓️ SESSION 1 (3 Weeks Ago) - Agent: gatekeeper_agent")
    print("==================================================================")

    session_1 = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id="zelda_session_101",
        state={"user:user_preferred_language": "English"}
    )

    runner_s1 = Runner(
        agent=gatekeeper_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service
    )

    msg_s1 = types.Content(
        role="user",
        parts=[types.Part.from_text(
            text="I used to hate seafood, but last night I tried salmon in Seattle and loved it!"
        )]
    )

    async for event in runner_s1.run_async(user_id=USER_ID, session_id="zelda_session_101", new_message=msg_s1):
        if event.is_final_response() and event.content:
            part = event.content.parts[0]
            if hasattr(part, "text") and part.text:
                print(f"Gatekeeper Output: {part.text}\n")

    # CRITICAL: Manually flush/add Session 1 into the Memory Bank
    print("--> Explicitly saving Session 1 to Vertex AI Memory Bank...")
    await memory_service.add_session_to_memory(session_1)

    print("\n==================================================================")
    print("⏳ Simulating 3-week gap (45s pause for GCP vector indexing)...")
    print("==================================================================")
    await asyncio.sleep(45)

    # ------------------------------------------------------------------------
    # SESSION 2: Today (Brand New Session ID: zelda_session_202)
    # ------------------------------------------------------------------------
    print("==================================================================")
    print("🗓️ SESSION 2 (Today) - Agent: recommendation_agent")
    print("==================================================================")

    await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id="zelda_session_202",
            state={"user:user_preferred_language": "English"}
        )

    runner_s2 = Runner(
            agent=recommendation_agent,
            app_name=APP_NAME,
            session_service=session_service,
            memory_service=memory_service
        )

    msg_s2 = types.Content(
            role="user",
            parts=[types.Part.from_text(text="What can I eat for dinner tonight?")]
        )

    print("--> Invoking Session 2 Runner (Querying Vertex AI Memory Bank)...")

    async for event in runner_s2.run_async(user_id=USER_ID, session_id="zelda_session_202", new_message=msg_s2):
        if event.is_final_response() and event.content:
            part = event.content.parts[0]
            if hasattr(part, "text") and part.text:
                print(f"\nRecommendation Agent Output:\n{part.text}\n")
        else:
            print(f"Intermediate Event: {event.type} - {event.content}")
if __name__ == "__main__":
    asyncio.run(main())