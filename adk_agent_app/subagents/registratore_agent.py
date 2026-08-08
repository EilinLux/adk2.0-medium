# agent/subagents/registratore_agent.py
from google.adk.agents.llm_agent import Agent
from adk_agent_app.tools.registratore_agent_tools import save_new_user_tool

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
    5. Explain that you are now passing them to the Cameriere to organize their trip.
    """,
    tools=[save_new_user_tool]
    )