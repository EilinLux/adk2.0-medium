from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from google.adk import Agent, Workflow, Event
from google.adk.events import RequestInput

# Mock database of registered users
REGISTERED_USER_DB = {
"usr_12345": {"name": "Alice"},
"usr_67890": {"name": "Bob"}
}

def is_registered_tool(user_id: str) -> Dict[str, Any]:
    """Verifies if a Sosta user ID is active and registered in the system database."""
    normalized_id = str(user_id).strip().lower()
    if normalized_id in REGISTERED_USER_DB:
        return {
        "status": "registered",
        "user_id": normalized_id,
        "data": REGISTERED_USER_DB[normalized_id]
        }
    return {"status": "unregistered", "user_id": normalized_id}

# ==========================================
# 1. Structured Output Schema for the Agent
# ==========================================
class UserExtraction(BaseModel):
    user_id: Optional[str] = Field(
    None,
    description="The extracted user ID. It must be strictly formatted (e.g., 'usr_12345')."
    )
    wants_to_register: bool = Field(
        ...,
        description="Set to True if the user says they are not registered, want to sign up, or don't have an ID."
        )

# ==========================================
# 2. Workflow Nodes
# ==========================================
# Node A: Pause and get raw input
def ask_user_for_id():
    yield RequestInput(
    message="Welcome to Sosta! Please enter your User ID, or type 'no' if you aren't registered yet:"
    )
# Node B: Use Gemini to cleanly extract the data
extractor_agent = Agent(
    name="extractor_agent",
    model="gemini-2.5-flash",
    instruction="""
    Analyze the user's input and fill out the response schema.
    Look for a user ID pattern starting with 'usr_' followed by numbers.
    If they explicitly state they are not registered, or say 'no', set wants_to_register to True.
    """,
    # Enforce structured output via output_schema
    output_schema=UserExtraction
    )

# Node C: The Deterministic Router (now receives clean structured data!)
def router(node_input: UserExtraction) -> Event:
    """Routes the user based on the clean structured data from the extractor agent."""
    # 1. If the LLM determined they want to register (or didn't provide an ID)
    if node_input.wants_to_register or not node_input.user_id:
        return Event(route="RUN_AGENT_REGISTRATORE")
    # 2. Check our DB with the clean, extracted ID
    result = is_registered_tool(node_input.user_id)
    if result.get("status") == "registered":
        return Event(route="RUN_AGENT_CAMERIERE")
    return Event(route="RUN_AGENT_REGISTRATORE")
# ==========================================
# 3. Specialists (Execution Nodes)
# ==========================================
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
# ==========================================
# 4. The Orchestration Graph
# ==========================================
root_agent = Workflow(
    name="routing_workflow",
    edges=[
        # START -> Pause for input -> Pass input to Extractor -> Pass structured data to Router
        ("START", ask_user_for_id, extractor_agent),
        (extractor_agent, router),
        # Router executes the correct specialist agent
        (router,
            {
            "RUN_AGENT_CAMERIERE": cameriere_agent,
            "RUN_AGENT_REGISTRATORE": registratore_agent,
            },
        ),
    ],
)