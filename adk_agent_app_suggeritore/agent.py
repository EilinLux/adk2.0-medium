# adk_agent_app_suggeritore/agent.py
import os

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent
from google.adk.tools import AgentTool

from .subagents.menu_checker_agent import menu_checker_agent
from .subagents.route_planner_agent import route_planner_agent
from .subagents.soste_search_agent import soste_search_agent

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

# Configure A2A public RPC endpoint (supports local port 8001 and Cloud Run HTTPS URLs)
from urllib.parse import urlparse
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from .subagents.soste_search_agent import MCP_SSE_URL

a2a_public_url = os.getenv("A2A_PUBLIC_URL")
if a2a_public_url:
    parsed_url = urlparse(a2a_public_url)
    a2a_protocol = parsed_url.scheme or "https"
    a2a_host = parsed_url.hostname or "localhost"
    a2a_port = parsed_url.port or (443 if a2a_protocol == "https" else 80)
else:
    a2a_protocol = os.getenv("A2A_PROTOCOL", "http")
    a2a_host = os.getenv("A2A_HOST", "localhost")
    a2a_port = int(os.getenv("A2A_PORT", "8001"))

# Expose the agent as an A2A ASGI Starlette application
a2a_app = to_a2a(
    agent,
    host=a2a_host,
    port=a2a_port,
    protocol=a2a_protocol,
)


class CloudRunA2AMiddleware(BaseHTTPMiddleware):
    """Provides Cloud Run /health probes and dynamically resolves the public AgentCard RPC URL from X-Forwarded headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ("/health", "/health/live", "/health/ready"):
            return JSONResponse(
                {
                    "status": "ok",
                    "service": "sosta-suggeritore-a2a",
                    "agent": agent.name,
                    "mcp_sse_url": MCP_SSE_URL,
                }
            )

        response = await call_next(request)

        # When hosted behind Cloud Run's HTTPS proxy without a hardcoded A2A_PUBLIC_URL,
        # rewrite the AgentCard's "url" field using X-Forwarded-Proto and Host headers
        # so RemoteA2aAgent posts JSON-RPC messages to the public Cloud Run HTTPS URL.
        if (
            request.url.path in ("/.well-known/agent-card.json", "/.well-known/agent.json")
            and response.status_code == 200
            and not os.getenv("A2A_PUBLIC_URL")
        ):
            forwarded_proto = request.headers.get("x-forwarded-proto")
            host_header = request.headers.get("host")
            if forwarded_proto and host_header:
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk
                try:
                    card_data = json.loads(body_bytes.decode("utf-8"))
                    card_data["url"] = f"{forwarded_proto}://{host_header}/"
                    return JSONResponse(card_data, status_code=200)
                except Exception:
                    return Response(
                        content=body_bytes,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )

        return response


a2a_app.add_middleware(CloudRunA2AMiddleware)

