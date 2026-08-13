# adk_agent_app/subagents/registratore_agent.py
from google.adk.agents import Agent

from ..callbacks import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from ..tools.registratore_agent_tools import save_new_user_tool
from ..schemas.user_schemas import RegistrationSummaryOutput

# Note on Peer Agent Transfer:
# In ADK LlmAgent, `disallow_transfer_to_peers` and `disallow_transfer_to_parent` default to False,
# allowing Registratore to transfer directly to its peer Cameriere via `transfer_to_agent`.
# Avoid phrasing like "Explain that you are now passing them to the Cameriere...", as it can cause
# the LLM to merely inform the user instead of executing `transfer_to_agent(agent_name='Cameriere')` in the same turn.
registratore_agent = Agent(
    name="Registratore",
    model="gemini-2.5-flash",
    description="Handles onboarding and account creation for NEW users by collecting profile data.",
    instruction="""
    You are the registration assistant for Sosta. Your task is to collect complete profile details from new users and onboard them.

    1. COLLECT REQUIRED PROFILE DATA:
       Prompt the user naturally (one question at a time if they haven't provided everything yet) to gather these 5 required profile attributes:
       - Full Name (`full_name`)
       - Email Address (`email`)
       - Preferred Language (`preferred_language`)
       - Culinary / Dietary Preferences (`culinary_preferences`, e.g., `["Vegan"]`, `["Vegetarian"]`, `["Gluten-free"]`; if the user eats everything or has no restrictions, pass `["No specific preferences"]`)
       - Vehicle Type (`vehicle_type`, e.g., `"Electric"`, `"Gasoline"`, `"Hybrid"`)

    2. PERSIST USER DATA:
       Once you have collected all 5 required attributes, call the `save_new_user` tool immediately.
       Do not ask for extra vehicle details like battery capacity or connector type.

    3. CONFIRM & HAND OFF:
       Immediately after `save_new_user` succeeds, invoke `transfer_to_agent(agent_name='Cameriere')` in the same turn so Cameriere can greet the user and organize their trip.
    """,
    tools=[save_new_user_tool],
    output_key="raw_registration_result",  # Saves output text/result to session state
    before_model_callback=before_model_guardrail,
    after_model_callback=after_model_guardrail,
    before_tool_callback=before_tool_guardrail,
    after_tool_callback=after_tool_guardrail,
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