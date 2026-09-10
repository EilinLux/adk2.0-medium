import asyncio
import warnings
from typing import Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.adk.memory import VertexAiMemoryBankService
from agentplatform import Client as agentplatform_client



# Suppress JSON_SCHEMA experimental warning
warnings.filterwarnings("ignore", message=".*JSON_SCHEMA_FOR_FUNC_DECL.*")
import warnings
# Suppress the vertexai deprecation warning from the Google ADK library
warnings.filterwarnings(
    "ignore", 
    category=FutureWarning, 
    module="google.adk.memory.vertex_ai_memory_bank_service"
)

# Import environment variables from .env file
load_dotenv()

def create_memory_bank_and_client():
    """ Creates a Vertex AI Memory Bank and returns the client and agent engine ID."""
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
    return client, agent_engine_id

class PreferenceData(BaseModel):
    """Key-value pairs of extracted user preferences (e.g., {'culinary_preference': 'Salmon'})"""
    culinary_preference: str = Field(
        description="The primary culinary preference or food liked by the user (e.g. 'Salmon')"
    )


async def search_mock_restaurant_api(cuisine: str, tool_context: ToolContext) -> dict:
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


def create_agents():
    """
    Creates the agents for handling user interactions.
    """

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
    """Main function to run the memory bank test scenario.
        This function simulates two sessions:   
        1. A historical session where the user expresses a new culinary preference.
        2. A current session where the user asks for dinner suggestions, and the system retrieves prior context from the memory bank.
    
    """
    # Constants for the application and user
    APP_NAME = "sosta_app"
    USER_ID = "user_zelda"


    # 1. Setup Session Service and Vertex AI Memory Bank
    session_service = InMemorySessionService()

    # 2. Create Vertex AI Memory Bank and Client
    ap_client, agent_engine_id = create_memory_bank_and_client()

    # 3. Initialize Vertex AI Memory Bank Service
    memory_service = VertexAiMemoryBankService(agent_engine_id=agent_engine_id)


    # 4. Create Agents
    gatekeeper_agent, recommendation_agent = create_agents()

    # 5. Shared App-Scoped Configuration across all users
    global_app_config = {
        "app:enable_beta_recommendations": True,
        "app:system_version": "2.1.0"
    }


    print("==================================================================")
    print("SESSION 1: Historical Interaction (3 Weeks Ago)")
    print("==================================================================")

    # 1. Initialize session for the past conversation
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

    # 2. Simulate a historical user message expressing a new culinary preference
    historical_msg = types.Content(
        role="user",
        parts=[types.Part.from_text(
            text="I used to hate seafood, but last night I tried salmon in Seattle and loved it! Oh, and my dog Max loved the trip too."
        )]
    )

    # 3. Initialize Runner for the gatekeeper agent to process the historical message, which extracts the culinary preference and updates the session state
    runner_gatekeeper = Runner(agent=gatekeeper_agent, app_name=APP_NAME, session_service=session_service)

    # 4. Process the historical message and print the parsed output
    print("\n--- Processing Historical Statement ---")
    for turn in runner_gatekeeper.run(user_id=USER_ID, session_id="zelda_session_1", new_message=historical_msg):
        if turn.content and turn.content.parts:
            for part in turn.content.parts:
                if part.text:
                    print(f"Gatekeeper Parsed: {part.text}")


    # 5. Save session turn to Vertex AI Memory Bank
    updated_zelda_s1 = await session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id="zelda_session_1")
    await memory_service.add_session_to_memory(updated_zelda_s1)

    # 6. Wait for memory bank indexing to complete (non-blocking)
    print("\n==================================================================")
    print(" Waiting for memory bank indexing (non-blocking async sleep)...")
    print("\n==================================================================")
    await asyncio.sleep(45)  # Adjust this duration based on expected indexing time

    print("\n==================================================================")
    print("SESSION 2: Current Session Query ('What can I eat for dinner?')")
    print("==================================================================")

    # 7. Search long-term memory for past food/culinary preferences
    results = await memory_service.search_memory(
        app_name=APP_NAME,
        user_id=USER_ID,
        query="what food or culinary preferences does the user have?"
    )
    
    print(f"Memory Bank Search Results: {results.memories}")
    # 8. Extract prior context from memory search results to include in the new session state
    prior_context = "\n".join(
        [
            part.text
            for r in results.memories
            if r.content and r.content.parts
            for part in r.content.parts
            if part.text
        ]
    )

    # 9. Create a fresh session representing today's conversation, including the prior context from memory
    zelda_s2 = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id="zelda_session_2",
        state={
            **global_app_config,
            "user:user_preferred_language": "English",
            "user:prior_context": prior_context,
            "current_subagent": "recommendation_agent"
        }
    )

    #  10. Initialize Runner for the recommendation agent to process the current dinner query
    runner_recommendation = Runner(agent=recommendation_agent, app_name=APP_NAME, session_service=session_service)

    # 11. User asks what to eat for dinner
    dinner_query = types.Content(
        role="user",
        parts=[types.Part.from_text(text="What can I eat for dinner?")]
    )

    # 12. Process the dinner query and print the recommendation agent's output
    print("\n--- Recommendation Agent Processing Query ---")
    try:
        for turn in runner_recommendation.run(user_id=USER_ID, session_id="zelda_session_2", new_message=dinner_query):
            if turn.content and turn.content.parts:
                for part in turn.content.parts:
                    if part.text:
                        print(f"Agent Output: {part.text}")
                
    except Exception as e:
        print(f"Error during recommendation agent run: {e}")
    
if __name__ == "__main__":
    asyncio.run(main())


"""
finally:
# Force deletion of the Reasoning Engine and all attached child memories
print(f"\nCleaning up Memory Bank: {agent_engine_id}")
ap_client.agent_engines.delete(
    name=f"projects/{os.getenv('PROJECT_NUMBER')}/locations/europe-west1/reasoningEngines/{agent_engine_id}",
    force=True
)   
"""   