from google.adk.tools import FunctionTool

CITY_COORDINATES = {
    "milano": {"lat": 45.4642, "lon": 9.1900},
    "bologna": {"lat": 44.4949, "lon": 11.3426},
    "firenze": {"lat": 43.7696, "lon": 11.2558},
    "roma": {"lat": 41.8919, "lon": 12.5113},
    "napoli": {"lat": 40.8518, "lon": 14.2681},
    "torino": {"lat": 45.0703, "lon": 7.6869},
    "venezia": {"lat": 45.4408, "lon": 12.3155},
    "bari": {"lat": 41.1171, "lon": 16.8719}
}

def calculate_route_and_target_stop(
    origin_city: str = "Milano", 
    destination_city: str = "Roma"
) -> dict:
    """
    Calculates the route and determines the ideal midpoint coordinates (latitude, longitude)
    for a refueling/charging and dining stop based on travel direction.
    """
    orig_clean = (origin_city or "Milano").lower().strip()
    dest_clean = (destination_city or "Roma").lower().strip()

    orig_coords = CITY_COORDINATES.get(orig_clean, CITY_COORDINATES["milano"])
    dest_coords = CITY_COORDINATES.get(dest_clean, CITY_COORDINATES["roma"])

    # Midpoint along the route
    target_lat = (orig_coords["lat"] + dest_coords["lat"]) / 2
    target_lon = (orig_coords["lon"] + dest_coords["lon"]) / 2

    return {
        "origin_city": origin_city,
        "destination_city": destination_city,
        "direction": f"From {origin_city} to {destination_city}",
        "target_stop_coordinates": {
            "latitude": round(target_lat, 4),
            "longitude": round(target_lon, 4)
        },
        "suggested_stop_reason": "Ideal midpoint along the route for a driving break, dining, and refueling/charging."
    }

route_generator_tool = FunctionTool(calculate_route_and_target_stop)
