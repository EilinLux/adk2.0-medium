from google.adk.agents import Agent
from ..tools.suggeritore_agent_route_tools import route_generator_tool
from mcp import ClientSession
from mcp.client.sse import sse_client
import os

MCP_PORT = os.getenv("MCP_PORT", "8002")
MCP_SSE_URL = f"http://127.0.0.1:{MCP_PORT}/sse"

# Definiamo la funzione asincrona che l'ADK eseguirà direttamente quando l'agente la chiama
async def get_mcp_soste_session(latitude: float, longitude: float, fuel_type: str = None) -> str:
    """
    Searches BigQuery for highway service areas and restaurants near target coordinates matching fuel requirements.
    """
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Argomenti da passare al FastMCP tool
            args = {
                "latitude": latitude,
                "longitude": longitude
            }
            if fuel_type:
                args["fuel_type"] = fuel_type
                
            result = await session.call_tool("find_soste_by_fuel_and_location", arguments=args)
            return str(result.content)
        
 


# SUB-AGENT 1: Route Planner
route_planner_agent = Agent(
    name="RoutePlannerAgent",
    model="gemini-2.5-flash",
    description="Calculates route direction and target midpoint stop coordinates for a given origin and destination city.",
    instruction="""
    You are the Route Planner Specialist.
    When given origin and destination cities, call 'calculate_route_and_target_stop' to determine 
    the optimal midpoint stop coordinates (latitude and longitude).
    Return the coordinates and route summary clearly.
    """,
    tools=[route_generator_tool]
)

# SUB-AGENT 2: Highway Stops Search
soste_search_agent = Agent(
    name="SosteSearchAgent",
    model="gemini-2.5-flash",
    description="Searches BigQuery for highway service areas and restaurants near target coordinates matching vehicle fuel or charging requirements.",
    instruction="""
    You are the Highway Service Areas Specialist.
    Call 'get_mcp_soste_session' using the latitude, longitude, and required fuel/charging type.
    If no stops are found for a specific fuel type, retry without the fuel_type filter to return all available nearby stops.
    """,
    tools=[get_mcp_soste_session]  # Using the MCP session for BigQuery access
    #tools=[soste_search_tool]   # Using the FunctionTool for BigQuery access
)

# SUB-AGENT 3: Menu & Dietary Checker
menu_checker_agent = Agent(
    name="MenuCheckerAgent",
    model="gemini-2.5-flash",
    description="Evaluates restaurant services and menu options against user and companion dietary preferences.",
    instruction="""
    You are a Dining and Dietary Specialist.
    Review the list of highway stops provided to you and compare their available services and dining options against the user's dietary preferences.
    Highlight special amenities (e.g., 'FRESH_PASTRY', 'PANORAMIC_VIEW') and rank the best matching options.
    """
)