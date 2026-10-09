# adk_agent_app_suggeritore/subagents/soste_search_agent.py
import os
from typing import Optional
from urllib.parse import urlparse

from google.adk.agents import Agent
from mcp import ClientSession
from mcp.client.sse import sse_client

from ..schemas.suggeritore_schemas import SosteSearchInput
from ..tools.suggeritore_agent_bq_soste_tools import soste_search_tool

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
