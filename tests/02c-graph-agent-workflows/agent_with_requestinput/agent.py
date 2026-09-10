from typing import Dict, Any
from google.adk import Agent, Workflow, Event
from google.adk.events import RequestInput  # Import the HITL event

# Mock database of registered users
REGISTERED_USER_DB = {
    "usr_12345": {"name": "Alice", "email": "alice@example.com"},
    "usr_67890": {"name": "Bob", "email": "bob@example.com"}
}

def is_registered_tool(user_id: str) -> Dict[str, Any]:
    """Verifies if a Sosta user ID is active and registered in the system database."""
    normalized_id = str(user_id).strip()
    if normalized_id in REGISTERED_USER_DB:
        return {
            "status": "registered",
            "user_id": normalized_id,
            "message": "User validation successful.",
            "data": REGISTERED_USER_DB[normalized_id]
        }
    return {
        "status": "unregistered",
        "user_id": normalized_id,
        "message": "No matching user record found in Sosta DB."
    }

# 1. HITL Node (Pauses and waits for user response)
def ask_user_for_id():
    """
    Greets the user and explicitly requests their ID.
    Yielding RequestInput tells ADK to stop running and wait for a response.
    """
    yield RequestInput(
        message="Welcome to Sosta! To get started, please enter your User ID, or type 'no' if you aren't registered yet:"
    )

# 2. Routing Node (Receives the human input)
def router(node_input) -> Event:  # Use 'node_input'
    """Routes the user deterministically based on their provided input."""
    # Convert the node input directly to a string
    user_id = str(node_input).strip()
    
    # If the user says they aren't registered, bypass DB lookups
    if user_id.lower() in ["no", "none", "not registered", "register"]:
        return Event(route="RUN_AGENT_REGISTRATORE")
        
    # Check the database
    result = is_registered_tool(user_id)
    
    # Check the return dictionary status
    if result.get("status") == "registered":
        return Event(route="RUN_AGENT_CAMERIERE")
        
    return Event(route="RUN_AGENT_REGISTRATORE")

# 3. Execution Nodes (Specialists)
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
    instruction="""Help the registered user plan thier stop:
    1. Ask if they are traveling with anyone else and if those companions have dietary preferences.
    2. Ask what their final destination is.
    3. IF the user provides a city or place name, NEVER ask for coordinates. 
    4. Summarize all gathered info (ID, Profile, Companions, Destination) for the Suggeritore.
    """
)

# 4. The Orchestration Graph
root_agent = Workflow(
    name="routing_workflow",
    edges=[
        # Pauses on ask_user_for_id. On resume, passes user reply directly to router.
        ("START", ask_user_for_id, router),
        
        # Route to the appropriate specialist agent
        (
            router,
            {
                "RUN_AGENT_CAMERIERE": cameriere_agent,
                "RUN_AGENT_REGISTRATORE": registratore_agent,
            },
        ),
    ],
)