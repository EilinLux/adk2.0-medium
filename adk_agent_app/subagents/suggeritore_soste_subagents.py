# adk_agent_app/subagents/suggeritore_soste_subagents.py
from pathlib import Path
import sys
from typing import Optional

from google.adk.agents import Agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..schemas.suggeritore_schemas import (
    MenuCheckerInput,
    RoutePlannerInput,
    SosteSearchInput,
)
from ..tools.suggeritore_agent_bq_soste_tools import soste_search_tool
from ..tools.suggeritore_agent_food_kb_rag_tools import (
    product_specs_rag_tool,
    stop_food_kb_tool,
)
from ..tools.suggeritore_agent_route_tools import route_generator_tool

# 1. Resolve the absolute path of the MCP Server script safely
CURRENT_DIR = Path(__file__).parent.resolve()
FAST_MCP_SCRIPT_PATH = str(
    CURRENT_DIR.parent / "tools" / "suggeritore_agent_bq_mcp_soste_tool.py"
)

# 2. Use the active virtual environment Python interpreter (sys.executable)
mcp_params = StdioServerParameters(
    command=sys.executable,
    args=[FAST_MCP_SCRIPT_PATH],
)


# 3. Define the async tool function that ADK executes when SosteSearchAgent invokes it
async def get_mcp_soste_session(
    latitude: float,
    longitude: float,
    fuel_type: Optional[str] = None,
) -> str:
    """Searches BigQuery via the MCP Server for highway service areas and restaurants near target coordinates.

    Args:
        latitude: Target midpoint latitude coordinate.
        longitude: Target midpoint longitude coordinate.
        fuel_type: Optional required vehicle fuel or charging type (e.g., 'ELECTRIC_FAST', 'GASOLINE').

    Returns:
        str: Stringified MCP tool execution content containing matching highway stops.
    """
    async with stdio_client(mcp_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Arguments forwarded to the MCP tool 'find_soste_by_fuel_and_location'
            args = {
                "latitude": latitude,
                "longitude": longitude,
            }
            if fuel_type:
                args["fuel_type"] = fuel_type

            result = await session.call_tool(
                "find_soste_by_fuel_and_location", arguments=args
            )
            return str(result.content)


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

# SUB-AGENT 2: Highway Stops Search (via MCP Server)
soste_search_agent = Agent(
    name="SosteSearchAgent",
    model="gemini-2.5-flash",
    description="Searches BigQuery for highway service areas and restaurants near target coordinates matching vehicle fuel or charging requirements.",
    instruction="""
    You are the Highway Service Areas Specialist.
    Call `get_mcp_soste_session` using the `latitude`, `longitude`, and `fuel_type` provided in the input JSON.
    If no stops are found for a specific fuel type, retry without the `fuel_type` filter to return all available nearby stops.
    Return the list of stops found, including their exact `stop_name`, `fuel_types`, `services`, and `distance_meters`.
    """,
    input_schema=SosteSearchInput,
    tools=[get_mcp_soste_session],  # Using the MCP session for BigQuery access
    # tools=[soste_search_tool]     # Using the FunctionTool for BigQuery access
)

# SUB-AGENT 3: Menu & Dietary Checker (Firestore Food KB + Vertex AI RAG over Product Spec PDFs)
menu_checker_agent = Agent(
    name="MenuCheckerAgent",
    model="gemini-2.5-flash",
    description="Evaluates restaurant services and menu options against user and companion dietary preferences using the Firestore Food KB and Product Specification RAG.",
    instruction="""
    You are a Dining and Dietary Specialist.
    1. First, call `get_stop_food_inventory_and_reviews` with the `stop_names` provided in the input JSON to inspect the stocked food items and traveler reviews at each stop.
    2. Next, call `retrieve_product_specs_rag` with a query combining the candidate food products and `dietary_preferences` to verify exact ingredients, allergen declarations ('CONTAINS' vs 'FREE FROM'), and certifications from the official Product Specification PDFs.
    3. Evaluate each stop in `stop_names`, highlighting which specific stocked items are verified safe for the traveler's `dietary_preferences` (such as 'Vegan Salad' / 'Vegan Rainbow Salad' and 'Espresso Coffee' at Secchia Ovest, or 'Fruit Bowl' at Sillaro Ovest) and which items contain restricted allergens.
    """,
    input_schema=MenuCheckerInput,
    tools=[stop_food_kb_tool, product_specs_rag_tool],
)