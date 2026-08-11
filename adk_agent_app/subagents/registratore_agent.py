# agent/subagents/registratore_agent.py
from google.adk.agents import Agent
from ..tools.registratore_agent_tools import save_new_user_tool
from ..schemas.user_schemas import RegistrationSummaryOutput

registratore_agent = Agent(
    name="Registratore",
    model="gemini-2.5-flash",
    description="Handles onboarding and account creation for NEW users by collecting profile data.",
    instruction="""
    You are the registration assistant for Sosta. Your task is to collect complete profile details from new users and onboard them .

    1. COLLECT REQUIRED PROFILE DATA:
       Prompt the user naturally to gather any missing profile attributes:
       - Full Name (`full_name`)
       - Email Address (`email`)
       - Preferred Language (`preferred_language`)
       - Culinary / Dietary Preferences (`culinary_preferences`, e.g., Vegetarian, Gluten-free)
       - Vehicle Type (`vehicle_type`, e.g., Electric, Gasoline, Hybrid)

    2. PERSIST USER DATA:
       Once you have collected all required information, call the `save_new_user` tool immediately. 
       Do not invent or mock missing values—ask the user directly if anything is missing.

    3. CONFIRM & HAND OFF:
       - Inform the user that their registration is complete and share their newly generated User ID.
       - Politely explain that you are handing them over to the Cameriere (Dining Concierge) to help organize their trip.
       - invoke transfer_to_agent('Cameriere') immediately
    """,
    tools=[save_new_user_tool],
    output_key="raw_registration_result"  # Saves output text/result to session state
)

# 2. Downstream Formatter Agent (Applies output_schema strictly without tools)
registration_formatter_agent = Agent(
    name="RegistrationFormatter",
    model="gemini-2.5-flash",
    description="Formats raw registration output into structured JSON for downstream orchestrators.",
    instruction="""
    Extract the registration status, user_id, full_name, and preferred_language from this execution result:
    {raw_registration_result}

    Respond ONLY with valid JSON matching the provided output schema. No markdown fences, no preamble.
    """,
    output_schema=RegistrationSummaryOutput,  # Enforces Pydantic contract
    output_key="structured_registration_summary"
)