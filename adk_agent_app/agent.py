# agent/gatekeeper_agent.py
from google.adk.agents.llm_agent import Agent
from adk_agent_app.tools.gatekeeper_tools import is_registered_user_tool
from adk_agent_app.subagents.registratore_agent import registratore_agent
from adk_agent_app.subagents.cameriere_agent import cameriere_agent

root_agent = Agent(
    name="Gatekeeper",
    model="gemini-2.5-flash",
    description="Root agent for the Sosta app", 
    instruction="""
    You are the welcoming Gatekeeper of the Sosta app. 
    
    1. Greet the user politely and ask if they are already registered.
    2. IF YES: Ask for their User ID and use 'verify_user_id' to check it.
       - If it exists, transfer them to the 'Cameriere'.
       - If not, inform them there was an error and ask to try again.
    3. IF NO: Ask if they want to register.
       - If yes, transfer them to the 'Registratore'.
       - If no, politely say goodbye and end the conversation.
    """,
    tools=[is_registered_user_tool],
    sub_agents=[registratore_agent, cameriere_agent] 
)