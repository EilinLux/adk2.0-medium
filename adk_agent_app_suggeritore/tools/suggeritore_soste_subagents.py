# adk_agent_app_suggeritore/tools/suggeritore_soste_subagents.py
import os
from typing import Optional

from google.adk.agents import Agent
from google.adk.code_executors import BuiltInCodeExecutor
from mcp import ClientSession
from mcp.client.sse import sse_client

from ..schemas.suggeritore_schemas import (
    MenuCheckerInput,
    RoutePlannerInput,
    SosteSearchInput,
    TripCalculatorInput,
)
from ..tools.suggeritore_agent_bq_soste_tools import soste_search_tool
from ..tools.suggeritore_agent_food_kb_rag_tools import (
    product_specs_rag_tool,
    stop_food_kb_tool,
)
from ..tools.suggeritore_agent_route_tools import route_generator_tool

from urllib.parse import urlparse

MCP_PORT = os.getenv("MCP_PORT", "8002")
MCP_SSE_URL = os.getenv("MCP_SSE_URL", f"http://127.0.0.1:{MCP_PORT}/sse")


def _get_mcp_auth_headers(mcp_url: str) -> dict[str, str]:
    """Fetches a Google Cloud OIDC ID token when connecting to a Cloud Run https://*.run.app MCP server."""
    if not mcp_url.startswith("https://"):
        return {}
    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import id_token

        parsed = urlparse(mcp_url)
        audience = f"{parsed.scheme}://{parsed.netloc}"
        token = id_token.fetch_id_token(GoogleAuthRequest(), audience)
        return {"Authorization": f"Bearer {token}"}
    except Exception:
        return {}


# Define the async tool function that ADK executes when SosteSearchAgent invokes it
async def get_mcp_soste_session(
    latitude: float,
    longitude: float,
    fuel_type: Optional[str] = None,
) -> str:
    """Searches BigQuery via the MCP SSE Server for highway service areas and restaurants near target coordinates.

    Args:
        latitude: Target midpoint latitude coordinate.
        longitude: Target midpoint longitude coordinate.
        fuel_type: Optional required vehicle fuel or charging type (e.g., 'ELECTRIC_FAST', 'GASOLINE').

    Returns:
        str: Stringified MCP tool execution content containing matching highway stops.
    """
    headers = _get_mcp_auth_headers(MCP_SSE_URL)
    async with sse_client(MCP_SSE_URL, headers=headers, timeout=30.0) as (read, write):
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

# SUB-AGENT 2: Highway Stops Search (via MCP SSE Server)
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
    tools=[get_mcp_soste_session],  # Using the MCP SSE session for BigQuery access
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

# SUB-AGENT 4: EV Charging & Trip Cost Calculator (Gemini Sandboxed Code Execution)
trip_calculator_agent = Agent(
    name="TripCalculatorAgent",
    model="gemini-2.5-flash",
    description="Executes Python code in a sandboxed environment to compute exact EV charging energy (kWh), charging duration (minutes), electricity cost (EUR), and per-passenger bill split.",
    instruction="""
    You are a Quantitative Trip & EV Charging Analyst equipped with a Python Code Executor.
    You MUST write and execute Python code to compute the exact numbers for the input JSON parameters:
    - `energy_added_kwh = battery_capacity_kwh * ((target_soc_percent - current_soc_percent) / 100.0)`
    - `charging_time_minutes = (energy_added_kwh / charger_power_kw) * 60.0` (account for a 1.0 else exact formula above)
    - `charging_cost_eur = round(energy_added_kwh * cost_per_kwh_eur, 2)`
    - `total_stop_cost_eur = round(charging_cost_eur + dining_cost_eur, 2)`
    - `cost_per_passenger_eur = round(total_stop_cost_eur / max(passengers_count, 1), 2)`
    Always execute the Python script first, then return a concise summary with the exact computed figures:
    Energy Added (kWh), Charging Duration (minutes), Charging Cost (EUR), Total Stop Cost (EUR), and Cost Per Passenger (EUR).
    """,
    input_schema=TripCalculatorInput,
    code_executor=BuiltInCodeExecutor(),
)