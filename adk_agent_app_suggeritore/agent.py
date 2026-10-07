from google.adk.agents import Agent
from google.adk.tools import AgentTool
from .tools.suggeritore_soste_subagents import route_planner_agent, soste_search_agent, menu_checker_agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import os

# Force Vertex AI environment if project ID is present
if os.getenv("GOOGLE_CLOUD_PROJECT"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

agent = Agent(
    name="Suggeritore",
    model="gemini-2.5-flash",
    description="Orchestrates multi-agent trip optimization to find ideal stops based on charging/fuel and dining needs.",
    instruction="""
    You are Suggeritore, the Trip Optimization Orchestrator.
    Your job is to execute a strict 3-step sequential workflow by calling your sub-agents in order.

    1. WORKFLOW STEPS:
       - STEP 1 (Route & Coordinates): Call 'RoutePlannerAgent' providing the origin city (default 'Milano' if unspecified) and destination city.
       - STEP 2 (BigQuery Search): Call 'SosteSearchAgent' using the latitude, longitude returned from Step 1, and the vehicle's fuel/charging type (e.g., GASOLINE, DIESEL, ELECTRIC_FAST, ELECTRIC_ULTRAFAST).
       - STEP 3 (Dietary & Menu Match): Call 'MenuCheckerAgent' providing the stops found in Step 2 along with any dietary preferences specified by the user or companion.

    2. OUTPUT FORMAT:
       - Synthesize all findings into a clear, recommended itinerary presented in the language used by the user.
       - Include:
         * Stop name and location along the route.
         * Fuel / Charging availability matching the user's vehicle.
         * Why the dining options suit their dietary requirements.
    """,
    tools=[
        AgentTool(agent=route_planner_agent),
        AgentTool(agent=soste_search_agent),
        AgentTool(agent=menu_checker_agent)
    ]
)

# 2. Expose the agent as an A2A ASGI FastAPI application
a2a_app = to_a2a(agent, port=8001)