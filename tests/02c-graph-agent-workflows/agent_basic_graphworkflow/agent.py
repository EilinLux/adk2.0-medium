# tests/02c-graph-agent-workflows/agent_basic_graphworkflow/agent.py
from typing import Dict, Any
from google.adk import Agent, Workflow, Event

# Mock database of registered users
REGISTERED_USER_DB = {
    "usr_12345": {"name": "Alice", "email": "alice@example.com"},
    "usr_67890": {"name": "Bob", "email": "bob@example.com"}
}

# 1. Declare Execution Nodes (Specialists)
gatekeeper_agent = Agent(
    name="gatekeeper_agent",
    model="gemini-2.5-flash",
    instruction="Greet the user warmly and explain how Sosta can help them in finding the best stop considering their culinary preferences and vehicle type. Ask if they are already registered with Sosta. If they are, ask for their User ID and verify it. If they are not registered, ask if they would like to register.",
)

registratore_agent = Agent(
    name="registratore_agent",
    model="gemini-2.5-flash",
    instruction="""
    You are the registration assistant for Sosta.    
    1. Ask the user about their culinary preferences (e.g., vegan, gluten-free).
    2. Ask what type of vehicle they drive.
    3. Explain that you are now passing them to the Cameriere to organize their trip.
    """
)

cameriere_agent = Agent(
    name="cameriere_agent",
    model="gemini-2.5-flash",
    instruction="""
    Help the registered user plan their stop:
    1. Ask if they are traveling with anyone else and if those companions have dietary preferences.
    2. Ask what their final destination is.
    3. IF the user provides a city or place name, NEVER ask for coordinates. 
    4. Summarize all gathered info (ID, Profile, Companions, Destination) for the Suggeritore.
    """
)

# 2. Define the Programmatic Router (No LLM reasoning needed here)
def router(node_input: Any) -> Event:
    """Routes the user deterministically based on registration status."""
    user_id = node_input.get("user_id") if isinstance(node_input, dict) else None
    
    if user_id in REGISTERED_USER_DB:
        return Event(route="RUN_AGENT_CAMERIERE")
    return Event(route="RUN_AGENT_REGISTRATORE")

# 3. Assemble the Orchestration Graph
# Note: Without RequestInput, gatekeeper_agent pipes its output directly into router
# without pausing for the human's reply ("The Silence of the Graph").
root_agent = Workflow(
    name="routing_workflow",
    edges=[
        # Intro -> Router
        ("START", gatekeeper_agent, router),
        
        # Router branches deterministically based on its return Event
        (
            router,
            {
                "RUN_AGENT_CAMERIERE": cameriere_agent,
                "RUN_AGENT_REGISTRATORE": registratore_agent,
            },
        ),
    ],
)