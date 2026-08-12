import json
import os
from google.cloud import bigquery
import logging
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
load_dotenv()  # Load .env file 

# ==========================================
# 0. SETUP & DATABASE INITIALIZATION
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

mcp = MCPServer("BigQuery-Soste-Server")


FULL_TABLE_PATH = f"{os.getenv('GOOGLE_CLOUD_PROJECT')}.{os.getenv('DATASET_ID')}.{os.getenv('TABLE_ID')}"

try:
    bq_client = bigquery.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))

    logger.info(f"BigQuery client initialized for project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
except Exception as e:
    logger.error(f"Failed to initialize BigQuery client: {e}")
    bq_client = None


# 2. Expose the function using the @mcp.tool() decorator
@mcp.tool()
def find_soste_by_fuel_and_location(
    latitude: float,
    longitude: float,
    fuel_type: str = None,
    radius_meters: int = 150000,  # 150km default
    limit: int = 5
) -> str:
    """
    Queries BigQuery for highway service areas and restaurants within a search radius.
    Includes full execution logging for debugging.
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

    # Recupera i metadati della tabella senza eseguire query SQL
    table_ref = bq_client.get_table(FULL_TABLE_PATH)
    total_rows = table_ref.num_rows

    if total_rows == 0:
        err_msg = f"Big query table `{FULL_TABLE_PATH}` is empty! "
        logger.error(err_msg)
        return json.dumps({"error": err_msg})

    try:
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
                "GASOLINE": "GASOLINE", "BENZINA": "GASOLINE", "PETROL": "GASOLINE",
                "DIESEL": "DIESEL", "GASOLIO": "DIESEL",
                "LPG": "LPG", "GPL": "LPG",
                "METHANE": "METHANE", "METANO": "METHANE",
                "ELECTRIC": "ELECTRIC_FAST", "EV": "ELECTRIC_FAST",
                "ELECTRIC_FAST": "ELECTRIC_FAST", "ELECTRIC_ULTRAFAST": "ELECTRIC_ULTRAFAST",
                "ELECTRIC_STANDARD": "ELECTRIC_STANDARD"
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
            logger.warning("Primary query returned 0 rows. Attempting FALLBACK QUERY (ignoring fuel_type filter)...")
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
            logger.info(f"  Result #{idx}: {row.get('stop_name')} - Distance: {row.get('distance_meters')}m")

        logger.info("=" * 60)
        return json.dumps(results, ensure_ascii=False)

    except Exception as e:
        logger.error(f"EXCEPTION IN SOSTE_TOOLS: {str(e)}", exc_info=True)
        return json.dumps({"error": f"BigQuery Execution Exception: {str(e)}"})



if __name__ == "__main__":
    # Change transport from STDIO to SSE so it runs as a persistent web server
    mcp.run(transport="sse", host="127.0.0.1", port=8002)