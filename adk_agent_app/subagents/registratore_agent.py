# adk_agent_app/subagents/registratore_agent.py
from google.adk.agents.llm_agent import Agent
from adk_agent_app.tools.registratore_agent_tools import save_new_user_tool

# Note on Peer Agent Transfer:
# In ADK LlmAgent, `disallow_transfer_to_peers` and `disallow_transfer_to_parent` default to False,
# allowing Registratore to transfer directly to its peer Cameriere via `transfer_to_agent`.
# Avoid phrasing like "Explain that you are now passing them to the Cameriere...", as it can cause
# the LLM to merely inform the user instead of executing `transfer_to_agent(agent_name='Cameriere')` in the same turn.
registratore_agent = Agent(
    name="Registratore",
    model="gemini-2.5-flash",
    description="Handles onboarding for NEW users. Asks for culinary preferences and vehicle type.",
    instruction="""
    You are the registration assistant for Sosta.    
    1. Ask the user about their culinary preferences (e.g., vegan, gluten-free).
    2. Ask what type of vehicle they drive.
    3. Use the 'save_new_user' tool to save the data and generate an ID.
    4. Communicate the new User ID to the user clearly.
    5. Transfer the user to the 'Cameriere' agent to organize their trip.
    """,
    tools=[save_new_user_tool]
)