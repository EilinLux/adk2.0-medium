# adk_agent_app_suggeritore/tools/suggeritore_agent_bq_mcp_soste_tool.py
import json
import logging
import os
from pathlib import Path
import sys
from typing import Optional

from dotenv import load_dotenv
from google.cloud import bigquery
from mcp.server.mcpserver import MCPServer

load_dotenv()  # Load root .env file
load_dotenv(Path(__file__).parent.parent / ".env")  # Also load adk_agent_app_suggeritore/.env

# ==========================================
# 0. SETUP & DATABASE INITIALIZATION
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

mcp = MCPServer("BigQuery-Soste-Server")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "adk-workshop-sosta-app-dev")
BIGQUERY_DATASET = (
    os.getenv("BIGQUERY_DATASET")
    or os.getenv("DATASET_ID")
    or "soste_app_dev"
)
BIGQUERY_TABLE = (
    os.getenv("BIGQUERY_TABLE")
    or os.getenv("TABLE_ID")
    or "db_soste"
)

FULL_TABLE_PATH = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"

try:
    bq_client = bigquery.Client(project=PROJECT_ID)
    logger.info(
        f"BigQuery client initialized for project: {PROJECT_ID} (table: {FULL_TABLE_PATH})"
    )
except Exception as e:
    logger.error(f"Failed to initialize BigQuery client: {e}")
    bq_client = None


# 2. Expose the function using the @mcp.tool() decorator
@mcp.tool()
def find_soste_by_fuel_and_location(
    latitude: float,
    longitude: float,
    fuel_type: Optional[str] = None,
    radius_meters: int = 150000,  # 150km default
    limit: int = 5,
) -> str:
    """Queries BigQuery for highway service areas and restaurants within a search radius.

    Args:
        latitude: Target midpoint latitude coordinate.
        longitude: Target midpoint longitude coordinate.
        fuel_type: Optional vehicle fuel or charging type (e.g., 'ELECTRIC_FAST', 'GASOLINE').
        radius_meters: Search radius in meters around the target coordinates (default 150000).
        limit: Maximum number of stops to return (default 5).

    Returns:
        str: JSON-encoded list of matching highway stops or an error dictionary.
    """
    logger.info("=" * 60)
    logger.info("MCP TOOL CALLED: find_soste_by_fuel_and_location")
    logger.info(f"  -> Raw Input Latitude: {latitude} (type: {type(latitude)})")
    logger.info(f"  -> Raw Input Longitude: {longitude} (type: {type(longitude)})")
    logger.info(f"  -> Raw Input Fuel Type: {fuel_type} (type: {type(fuel_type)})")
    logger.info(f"  -> Raw Input Radius (m): {radius_meters}")
    logger.info(f"  -> Raw Input Limit: {limit}")

    if bq_client is None:
        err_msg = "BigQuery client is not initialized."
        logger.error(err_msg)
        return json.dumps({"error": err_msg})

    try:
        # Retrieve table metadata without running a full SQL scan
        table_ref = bq_client.get_table(FULL_TABLE_PATH)
        total_rows = table_ref.num_rows

        if total_rows == 0:
            err_msg = f"BigQuery table `{FULL_TABLE_PATH}` is empty!"
            logger.error(err_msg)
            return json.dumps({"error": err_msg})

        # Validate coordinates
        if latitude is None or longitude is None:
            err_msg = f"Invalid coordinates received: lat={latitude}, lon={longitude}"
            logger.error(err_msg)
            return json.dumps({"error": err_msg})

        lat_float = float(latitude)
        lon_float = float(longitude)

        # Base clause
        where_clauses = [
            f"ST_DWITHIN(coordinates, ST_GEOGPOINT({lon_float}, {lat_float}), {int(radius_meters)})"
        ]

        # Fuel filtering
        if fuel_type and isinstance(fuel_type, str) and fuel_type.strip():
            clean_fuel = fuel_type.upper().strip()
            # Map common LLM string variants to BigQuery enum strings
            fuel_mapping = {
                "GASOLINE": "GASOLINE",
                "BENZINA": "GASOLINE",
                "PETROL": "GASOLINE",
                "DIESEL": "DIESEL",
                "GASOLIO": "DIESEL",
                "LPG": "LPG",
                "GPL": "LPG",
                "METHANE": "METHANE",
                "METANO": "METHANE",
                "ELECTRIC": "ELECTRIC_FAST",
                "EV": "ELECTRIC_FAST",
                "ELECTRIC_FAST": "ELECTRIC_FAST",
                "ELECTRIC_ULTRAFAST": "ELECTRIC_ULTRAFAST",
                "ELECTRIC_STANDARD": "ELECTRIC_STANDARD",
            }
            mapped_fuel = fuel_mapping.get(clean_fuel, clean_fuel)
            logger.info(f"  -> Mapped fuel_type '{fuel_type}' to '{mapped_fuel}'")
            where_clauses.append(f"'{mapped_fuel}' IN UNNEST(fuel_types)")

        where_str = " AND ".join(where_clauses)

        query = f"""
            SELECT 
                stop_name,
                fuel_types,
                services,
                phone,
                ST_Y(coordinates) AS latitude,
                ST_X(coordinates) AS longitude,
                ROUND(ST_DISTANCE(coordinates, ST_GEOGPOINT({lon_float}, {lat_float}))) AS distance_meters
            FROM 
                `{FULL_TABLE_PATH}`
            WHERE 
                {where_str}
            ORDER BY 
                distance_meters ASC
            LIMIT {limit};
        """

        logger.info("EXECUTING PRIMARY BIGQUERY SQL:")
        logger.info(query)

        query_job = bq_client.query(query)
        results = [dict(row) for row in query_job.result()]

        logger.info(f"PRIMARY QUERY EXECUTED SUCCESSFULLY. Rows returned: {len(results)}")

        # FALLBACK: If primary query returned 0 rows and fuel_type was used, retry without fuel_type
        if not results and fuel_type:
            logger.warning(
                "Primary query returned 0 rows. Attempting FALLBACK QUERY (ignoring fuel_type filter)..."
            )
            fallback_query = f"""
                SELECT 
                    stop_name,
                    fuel_types,
                    services,
                    phone,
                    ST_Y(coordinates) AS latitude,
                    ST_X(coordinates) AS longitude,
                    ROUND(ST_DISTANCE(coordinates, ST_GEOGPOINT({lon_float}, {lat_float}))) AS distance_meters
                FROM 
                    `{FULL_TABLE_PATH}`
                WHERE 
                    ST_DWITHIN(coordinates, ST_GEOGPOINT({lon_float}, {lat_float}), {int(radius_meters)})
                ORDER BY 
                    distance_meters ASC
                LIMIT {limit};
            """
            logger.info("EXECUTING FALLBACK BIGQUERY SQL:")
            logger.info(fallback_query)

            fallback_job = bq_client.query(fallback_query)
            results = [dict(row) for row in fallback_job.result()]
            logger.info(f"FALLBACK QUERY EXECUTED. Rows returned: {len(results)}")

        # Log found results
        for idx, row in enumerate(results, 1):
            logger.info(
                f"  Result #{idx}: {row.get('stop_name')} - Distance: {row.get('distance_meters')}m"
            )

        logger.info("=" * 60)
        return json.dumps(results, ensure_ascii=False)

    except Exception as e:
        logger.error(f"EXCEPTION IN SOSTE_TOOLS: {str(e)}", exc_info=True)
        return json.dumps({"error": f"BigQuery Execution Exception: {str(e)}"})


from starlette.requests import Request
from starlette.responses import JSONResponse


@mcp.custom_route("/health", methods=["GET"])
@mcp.custom_route("/health/live", methods=["GET"])
@mcp.custom_route("/health/ready", methods=["GET"])
async def mcp_health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Cloud Run startup and liveness probes."""
    return JSONResponse(
        {
            "status": "ok",
            "service": "sosta-mcp-sse",
            "project_id": PROJECT_ID,
            "table": FULL_TABLE_PATH,
        }
    )


if __name__ == "__main__":
    # Change transport from STDIO to SSE so it runs as a persistent web server.
    # On Cloud Run, PORT (default 8080) is injected and the server binds to 0.0.0.0.
    mcp_port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8002")))
    mcp_host = os.getenv("MCP_HOST", "0.0.0.0")
    mcp.run(transport="sse", host=mcp_host, port=mcp_port)