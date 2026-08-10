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


class PreferenceData(BaseModel):
    culinary_preference: str = Field(
        description="The primary culinary preference or food liked by the user (e.g. 'Salmon')"
    )


async def search_mock_restaurant_api(cuisine: str, tool_context: ToolContext) -> dict:
    tool_context.session.state["temp:raw_api_payload"] = {
        "status_code": 200,
        "results_count": 3,
        "raw_response_bytes": "0x4150495f5241575f44415441"
    }
    return {
        "status": "success",
        "message": f"Found 3 restaurants for cuisine/ingredient '{cuisine}'."
    }


def create_agents():
    gatekeeper_agent = Agent(
        name="gatekeeper_agent",
        model="gemini-2.5-flash",
        instruction="""
        You are a receptionist for sosta_app.
        Beta Recommendation Mode Status: {app:enable_beta_recommendations}
        
        Extract the user's culinary preference from their message using the provided output schema.
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
        
        Respond in the user's preferred language ({user:user_preferred_language}).
        Check past user preferences and memories retrieved from memory bank to suggest relevant options.
        Call search_mock_restaurant_api to find options if appropriate.
        """,
        tools=[search_mock_restaurant_api]
    )
    return gatekeeper_agent, recommendation_agent


async def main():
    APP_NAME = "sosta_app"
    USER_ID = "user_zelda"

    session_service = InMemorySessionService()
    ap_client, full_resource_name, agent_engine_id = create_memory_bank_and_client()
    memory_service = VertexAiMemoryBankService(agent_engine_id=agent_engine_id)

    gatekeeper_agent, recommendation_agent = create_agents()

    global_app_config = {
        "app:enable_beta_recommendations": True,
        "app:system_version": "2.1.0"
    }

    try:
        print("==================================================================")
        print("SESSION 1: Historical Interaction (3 Weeks Ago)")
        print("==================================================================")

        zelda_s1 = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id="zelda_session_1",
            state={
                **global_app_config,
                "user:user_preferred_language": "English",
                "current_subagent": "gatekeeper_agent",
            }
        )

        historical_msg = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="I used to hate seafood, but last night I tried salmon in Seattle and loved it! Oh, and my dog Max loved the trip too."
            )]
        )

        # Runner with Memory Service attached: Ingestion happens automatically
        runner_gatekeeper = Runner(
            agent=gatekeeper_agent,
            app_name=APP_NAME,
            session_service=session_service,
            memory_service=memory_service
        )

        print("\n--- Processing Historical Statement ---")
        for turn in runner_gatekeeper.run(user_id=USER_ID, session_id="zelda_session_1", new_message=historical_msg):
            if turn.content and turn.content.parts:
                for part in turn.content.parts:
                    if part.text:
                        print(f"Gatekeeper Parsed: {part.text}")

        print("\n==================================================================")
        print(" Waiting for memory bank indexing (non-blocking async sleep)...")
        print("==================================================================")
        await asyncio.sleep(20)  

        print("\n==================================================================")
        print("SESSION 2: Current Session Query ('What can I eat for dinner?')")
        print("==================================================================")

        # FIX 1: Ensure user:user_preferred_language is populated in state for Session 2
        zelda_s2 = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id="zelda_session_2",
            state={
                **global_app_config,
                "user:user_preferred_language": "English",  # Fixed KeyError
                "current_subagent": "recommendation_agent"
            }
        )

        # Runner with Memory Service attached: Retrieval happens automatically
        runner_recommendation = Runner(
            agent=recommendation_agent,
            app_name=APP_NAME,
            session_service=session_service,
            memory_service=memory_service
        )

        dinner_query = types.Content(
            role="user",
            parts=[types.Part.from_text(text="What can I eat for dinner?")]
        )

        print("\n--- Recommendation Agent Processing Query ---")
        for turn in runner_recommendation.run(user_id=USER_ID, session_id="zelda_session_2", new_message=dinner_query):
            if turn.content and turn.content.parts:
                for part in turn.content.parts:
                    if part.text:
                        print(f"Agent Output: {part.text}")

    finally:
        # FIX 2 & 3: Safe teardown handling with force=True and handling 404s
        print(f"\nCleaning up Memory Bank: {agent_engine_id}")
        try:
            ap_client.agent_engines.delete(name=full_resource_name, force=True)
            print("Memory Bank successfully deleted.")
        except ClientError as err:
            if err.code == 404:
                print("Memory Bank was already deleted or not found.")
            else:
                raise err


if __name__ == "__main__":
    asyncio.run(main())