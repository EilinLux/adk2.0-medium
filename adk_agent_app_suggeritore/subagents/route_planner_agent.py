# adk_agent_app_suggeritore/subagents/route_planner_agent.py
from google.adk.agents import Agent

from ..schemas.suggeritore_schemas import RoutePlannerInput
from ..tools.suggeritore_agent_route_tools import route_generator_tool

# SUB-AGENT 1: Route Planner
route_planner_agent = Agent(
    name="RoutePlannerAgent",
    model="gemini-2.5-flash",
    description="Calculates route direction and target midpoint stop coordinates for a given origin and destination city.",
    instruction="""
    You are the Route Planner Specialist.
    When given `origin_city` and `destination_city`, call `calculate_route_and_target_stop` to determine
    the optimal midpoint stop coordinates (`latitude` and `longitude`).
    Return the coordinates and route summary clearly.
    """,
    input_schema=RoutePlannerInput,
    tools=[route_generator_tool],
)
