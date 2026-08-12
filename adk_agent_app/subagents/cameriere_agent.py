# adk_agent_app/subagents/cameriere_agent.py
import os

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)
from google.adk.tools import preload_memory

from ..tools.cameriere_agent_tools import (
    extract_user_profile_tool,
    update_dietary_preferences_tool,
)

import httpx

SUGGERITORE_A2A_URL = os.getenv("SUGGERITORE_A2A_URL", "http://localhost:8001").rstrip("/")


class CloudRunOIDCAuth(httpx.Auth):
    """Attaches a Google Cloud OIDC ID token when calling https://*.run.app A2A services."""

    def __init__(self, target_audience: str):
        self.target_audience = target_audience.rstrip("/")

    def auth_flow(self, request: httpx.Request):
        if self.target_audience.startswith("https://"):
            try:
                from google.auth.transport.requests import Request as GoogleAuthRequest
                from google.oauth2 import id_token

                token = id_token.fetch_id_token(
                    GoogleAuthRequest(), self.target_audience
                )
                request.headers["Authorization"] = f"Bearer {token}"
            except Exception:
                pass
        yield request


# Create a RemoteA2aAgent that connects to our Suggeritore A2A Microservice
# This acts as a client-side proxy - Cameriere can transfer to it like a local sub-agent
suggeritore_agent = RemoteA2aAgent(
    name="Suggeritore",
    description="Orchestrates multi-agent trip optimization to find ideal stops based on charging/fuel and dining needs.",
    # Point to the agent card URL - this is where the A2A protocol metadata lives
    agent_card=f"{SUGGERITORE_A2A_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
    httpx_client=httpx.AsyncClient(
        timeout=600.0,
        auth=CloudRunOIDCAuth(SUGGERITORE_A2A_URL),
    ),
)


cameriere_agent = Agent(
    name="Cameriere",
    model="gemini-2.5-flash",
    description="Handles trip preparation and dining concierge services for verified users.",
    instruction="""
    You are Cameriere, the virtual waiter and dining concierge for Sosta.

    1. AUTOMATIC PROFILE HYDRATION:
       - Whenever control is transferred to you from Gatekeeper or Registratore (on your first turn in the conversation), you MUST IMMEDIATELY execute `extract_user_profile` using the verified User ID before replying, even if the user's details already appear in the conversation history.
       - LANGUAGE: Always speak in the language the user is CURRENTLY using in the conversation unless it is different from {user:preferred_language?}; if it is, greet the user by name ({user:name?}), note that their saved preferred language is {user:preferred_language?}, and ask which language they prefer to continue in. Once the language is established, ask if they are traveling with companions (and any dietary restrictions) and what their final destination is.

    2. CURRENT USER CONTEXT:
       - Guest Name: {user:name?}
       - Saved Dietary Preferences: {user:culinary_preferences?}
       - Vehicle Type: {user:vehicle_type?}

    3. INTERACTION & CONSTRAINTS:
       - DIETARY: If the user explicitly asks to add or change a dietary restriction in their profile (e.g., "Add Nut-free to my preferences"), execute `update_dietary_preferences`. If a newly mentioned food preference contradicts their saved `{user:culinary_preferences?}`, politely point out the contradiction and ask them to clarify their complete dietary preferences before updating their profile.
       - COMPANIONS: Ask about companions and their dietary restrictions. Store these under `trip:companion_preferences`.
       - DESTINATION: Ask for their final destination city/location. If the user provides a city or location name, NEVER ask for geographic coordinates (latitude/longitude). Store this under `trip:destination`.

    4. HANDOFF TO SUGGERITORE:
       - Summarize gathered details: User ID, Guest Name ({user:name?}), Vehicle ({user:vehicle_type?}), Primary Preferences ({user:culinary_preferences?}), Companions ({trip:companion_preferences?}), and Destination ({trip:destination?}), and ask the user if the summary is correct.
       - Once the user confirms the summary, invoke `transfer_to_agent(agent_name='Suggeritore')` immediately.
    """,
    tools=[extract_user_profile_tool, update_dietary_preferences_tool, preload_memory],
    sub_agents=[suggeritore_agent],
)
