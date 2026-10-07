# agent/tools/soste_tools.py
import json
from google.cloud import bigquery
from google.adk.tools import FunctionTool
import os 
from ..config import logger

from dotenv import load_dotenv

load_dotenv()  # Load .env file 


FULL_TABLE_PATH = f"{os.getenv('GOOGLE_CLOUD_PROJECT')}.{os.getenv('DATASET_ID')}.{os.getenv('TABLE_ID')}"


try:
    bq_client = bigquery.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))

    logger.info(f"BigQuery client initialized for project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
except Exception as e:
    logger.error(f"Failed to initialize BigQuery client: {e}")
    bq_client = None


def find_soste_by_fuel_and_location(
    latitude: float,
    longitude: float,
    fuel_type: str = None,
    radius_meters: int = 150000,  # 150km for sparse mock data
    limit: int = 5
) -> str:
    """
    Queries BigQuery for highway service areas and restaurants within a search radius.
    Includes full execution logging for debugging.
    """
    logger.info("=" * 60)
    logger.info("TOOL CALLED: find_soste_by_fuel_and_location")
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

        # FALLBACK 1: If primary query returned 0 rows and fuel_type was used, retry without fuel_type
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

        # FALLBACK 2: If still 0 rows, query the whole table to check if table is empty or has data
        if not results:
            logger.warning("Query returned 0 rows even with fallback. Checking table row count...")
            count_query = f"SELECT COUNT(*) as total_rows FROM `{FULL_TABLE_PATH}`"
            count_job = bq_client.query(count_query)
            count_res = list(count_job.result())
            total = count_res[0]["total_rows"] if count_res else 0
            logger.warning(f"Table `{FULL_TABLE_PATH}` total row count is: {total}")

            if total == 0:
                err_msg = f"Table `{FULL_TABLE_PATH}` is completely empty! Please run the seed script."
                logger.error(err_msg)
                return json.dumps({"error": err_msg})

            return json.dumps({"warning": f"No stops found within {radius_meters/1000}km of coordinates ({lat_float}, {lon_float})."})

        # Log found results
        for idx, row in enumerate(results, 1):
            logger.info(f"  Result #{idx}: {row.get('stop_name')} - Distance: {row.get('distance_meters')}m")

        logger.info("=" * 60)
        return json.dumps(results, ensure_ascii=False)

    except Exception as e:
        logger.error(f"EXCEPTION IN SOSTE_TOOLS: {str(e)}", exc_info=True)
        return json.dumps({"error": f"BigQuery Execution Exception: {str(e)}"})
    
soste_search_tool = FunctionTool(find_soste_by_fuel_and_location)