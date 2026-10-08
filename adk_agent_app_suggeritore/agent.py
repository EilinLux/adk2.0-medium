# adk_agent_app_suggeritore/agent.py
import os

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent
from google.adk.tools import AgentTool

from .tools.suggeritore_soste_subagents import (
    menu_checker_agent,
    route_planner_agent,
    soste_search_agent,
)

# Force Vertex AI environment if project ID is present
if os.getenv("GOOGLE_CLOUD_PROJECT"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

agent = Agent(
    name="Suggeritore",
    model="gemini-2.5-flash",
    description="Orchestrates multi-agent trip optimization to find ideal stops based on charging/fuel and dining needs.",
    instruction="""
    You are Suggeritore, the Trip Optimization Orchestrator.
    Your job is to execute a strict 3-step sequential workflow by calling your 3 AgentTools in order.

    1. WORKFLOW STEPS:
       - STEP 1 (Route & Coordinates): Call `RoutePlannerAgent` with `origin_city` (use `'Milano'` if unspecified) and `destination_city` (use the Italian city name: `'Roma'` for Rome, `'Firenze'` for Florence, `'Bologna'`, `'Napoli'`, `'Venezia'`, `'Torino'`, `'Bari'`).
       - STEP 2 (BigQuery Search): Call `SosteSearchAgent` using the exact `latitude` and `longitude` returned from Step 1, and map the vehicle's propulsion to `fuel_type`:
         * If the vehicle is Electric / EV -> pass `fuel_type='ELECTRIC_FAST'`
         * If the vehicle is Gasoline / Hybrid -> pass `fuel_type='GASOLINE'`
         * If the vehicle is Diesel -> pass `fuel_type='DIESEL'`
       - STEP 3 (Dietary & Menu Match): Call `MenuCheckerAgent` passing `stop_names` (the exact list of `stop_name` strings in the order returned by Step 2) and `dietary_preferences` (the list of dietary preferences from the user profile and companions, e.g., `['Vegan']` or `['No specific preferences']`).

    2. OUTPUT FORMAT:
       - Synthesize all findings into a concise, structured recommended itinerary presented in the language currently used by the user:
         * Greet the user by first name and state that you have optimized their trip from `<origin_city>` to `<destination_city>`.
         * Include header lines for `**Your Journey:** <origin_city> to <destination_city>` and `**Optimal Midpoint Stop:** Located near latitude <latitude>, longitude <longitude>.`
         * List each stop as a numbered item (`1. **<stop_name>**`, `2. **<stop_name>**`, etc.) with 3 concise bullets:
           - `* **Location:** Along your route from <origin_city> to <destination_city>.`
           - `* **Charging:** Equipped with **<fuel_type>** charging.`
           - `* **Dining for Vegans:** <1 concise sentence summarizing vegan options like salads, pasta with tomato sauce, and grilled vegetables>.`
         * Close with `Enjoy your trip to <destination_city>!`
    """,
    tools=[
        AgentTool(agent=route_planner_agent),
        AgentTool(agent=soste_search_agent),
        AgentTool(agent=menu_checker_agent),
    ],
)

# Alias root_agent so `adk eval adk_agent_app_suggeritore` and `adk web` can discover the agent
root_agent = agent

# Expose the agent as an A2A ASGI FastAPI application
a2a_app = to_a2a(agent, port=8001)
