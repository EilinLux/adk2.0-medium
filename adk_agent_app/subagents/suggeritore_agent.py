# adk_agent_app/subagents/suggeritore_agent.py
from google.adk.agents import Agent
from google.adk.tools import AgentTool

from .suggeritore_soste_subagents import (
    menu_checker_agent,
    route_planner_agent,
    soste_search_agent,
)

suggeritore_agent = Agent(
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
       - Synthesize all findings into a clear, recommended itinerary presented in the language currently used by the user.
       - Include:
         * Stop name and location along the route.
         * Fuel / Charging availability matching the user's vehicle.
         * Why the dining options suit their dietary requirements.
    """,
    tools=[
        AgentTool(agent=route_planner_agent),
        AgentTool(agent=soste_search_agent),
        AgentTool(agent=menu_checker_agent),
    ],
)
