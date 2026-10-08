# tests/03c-memory-test/memory_test_3_VertexAiMemoryBankService_in_Runner.py
"""
ADK 2.0 101 - Article 3c: VertexAiMemoryBankService Integrated in Runner
------------------------------------------------------------------------
This script demonstrates how to wire `VertexAiMemoryBankService` directly into the
ADK `Runner` and equip an agent with `preload_memory` / `load_memory` so it can
automatically recall past sessions without manual `search_memory()` plumbing:
1. Session 1 (3 Weeks Ago): User shares a new preference ("salmon in Seattle");
   session is ingested into Vertex AI Memory Bank via `add_session_to_memory()`.
2. Session 2 (Today): A brand-new session (`zelda_session_202`) runs with
   `Runner(..., memory_service=memory_service)` and `preload_memory` tool,
   automatically retrieving the salmon preference from Vertex AI Memory Bank.
"""
import asyncio
from typing import Any
import warnings

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from google.genai import types
from google.adk.agents import Agent
from google.adk.memory import VertexAiMemoryBankService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext, load_memory, preload_memory
from agentplatform import Client as agentplatform_client

# Suppress experimental warnings and deprecation notices
warnings.filterwarnings("ignore", message=".*JSON_SCHEMA_FOR_FUNC_DECL.*")
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="google.adk.memory.vertex_ai_memory_bank_service",
)

load_dotenv()

# ============================================================================
# 1. Structured Schemas & Custom Tools
# ============================================================================


class PreferenceExtraction(BaseModel):
    favorite_dish: str = Field(
        description="The user's favorite dish, ingredient, or culinary preference."
    )


async def search_mock_restaurant_api(cuisine: str, tool_context: ToolContext) -> dict[str, Any]:
    """Mock API tool that records execution state in temp: scope."""
    tool_context.state["temp:raw_api_payload"] = {
        "status_code": 200,
        "query": cuisine,
    }
    return {
        "status": "success",
        "message": f"Found 3 top-rated restaurants matching '{cuisine}'.",
    }


def create_memory_bank_and_client():
    """Creates a Vertex AI Memory Bank and returns the client, resource name, and numeric ID."""
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
# 2. Define the Specialized Micro-Agents
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

# Agent 2: Automatically preloads/queries long-term memory via Runner's memory_service
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
    1. Check the Extracted Preference ({user_information?}) or past conversation memories for preferred ingredients (e.g. salmon).
    2. Call `search_mock_restaurant_api` to search options for that ingredient/cuisine.
    3. Provide a friendly recommendation in the user's preferred language ({user:user_preferred_language?}).
    """,
    # preload_memory automatically injects relevant memories from Runner.memory_service
    # before each LLM turn; load_memory allows explicit on-demand memory lookup if needed.
    tools=[search_mock_restaurant_api, preload_memory, load_memory],
)


# ============================================================================
# 3. Execution Across 2 Independent Sessions
# ============================================================================


async def main():
    APP_NAME = "sosta_app"
    USER_ID = "user_zelda"

    session_service = InMemorySessionService()
    _, _, agent_engine_id = create_memory_bank_and_client()
    memory_service = VertexAiMemoryBankService(agent_engine_id=agent_engine_id)

    # ------------------------------------------------------------------------
    # SESSION 1: 3 Weeks Ago (Session ID: zelda_session_101)
    # ------------------------------------------------------------------------
    print("==================================================================")
    print("🗓️ SESSION 1 (3 Weeks Ago) - Agent: gatekeeper_agent")
    print("==================================================================")

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id="zelda_session_101",
        state={"user:user_preferred_language": "English"},
    )

    runner_s1 = Runner(
        agent=gatekeeper_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service,
    )

    msg_s1 = types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text="I used to hate seafood, but last night I tried salmon in Seattle and loved it!"
            )
        ],
    )

    async for event in runner_s1.run_async(
        user_id=USER_ID, session_id="zelda_session_101", new_message=msg_s1
    ):
        if event.is_final_response() and event.content:
            part = event.content.parts[0]
            if hasattr(part, "text") and part.text:
                print(f"Gatekeeper Output: {part.text}\n")

    # CRITICAL: Retrieve the updated session (containing the turn events) and ingest into Memory Bank
    print("--> Explicitly saving Session 1 to Vertex AI Memory Bank...")
    updated_session_1 = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id="zelda_session_101"
    )
    await memory_service.add_session_to_memory(updated_session_1)

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
        state={"user:user_preferred_language": "English"},
    )

    runner_s2 = Runner(
        agent=recommendation_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service,
    )

    msg_s2 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="What can I eat for dinner tonight?")],
    )

    print("--> Invoking Session 2 Runner (Querying Vertex AI Memory Bank via preload_memory)...")

    async for event in runner_s2.run_async(
        user_id=USER_ID, session_id="zelda_session_202", new_message=msg_s2
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    print(f"\nRecommendation Agent Output:\n{part.text}\n")
        elif event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    print(
                        f"Intermediate Tool Call ({event.author}): "
                        f"{part.function_call.name}({part.function_call.args})"
                    )


if __name__ == "__main__":
    asyncio.run(main())