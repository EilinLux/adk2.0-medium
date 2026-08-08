# agent/subagents/cameriere_agent.py
from google.adk.agents.llm_agent import Agent
from adk_agent_app.tools.cameriere_agent_tools import extract_user_profile_tool
#from adk_agent_app.subagents.suggeritore_agent import suggeritore_agent

cameriere_agent = Agent(
    name="Cameriere",
    model="gemini-2.5-flash",
    description="Handles trip preparation for EXISTING, verified users.",
    instruction="""
    You are the virtual Cameriere (Waiter). 
    
    1. Retrieve the verified User ID from the chat history.
    2. Use the 'extract_user_profile' tool to read their historical preferences, do not use this as prefered 
    language, use the one that the user used when started the conversation.
    3. Ask if they are traveling with anyone else and if those companions have dietary preferences.
    4. Ask what their final destination is.
    5. IF the user provides a city or place name, NEVER ask for coordinates. 
    6. Summarize all gathered info (ID, Profile, Companions, Destination) for the Suggeritore.
    """,
    tools=[extract_user_profile_tool],
    #sub_agents=[suggeritore_agent]
)


