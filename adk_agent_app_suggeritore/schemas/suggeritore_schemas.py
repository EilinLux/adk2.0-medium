# adk_agent_app_suggeritore/schemas/suggeritore_schemas.py
from typing import List, Optional
from pydantic import BaseModel, Field


class TripOptimizationRequest(BaseModel):
    """Input payload passed to Suggeritore to trigger the multi-agent optimization."""

    user_id: str = Field(description="Unique identifier for the user.")
    destination: str = Field(description="Final trip destination city or landmark.")
    vehicle_type: str = Field(
        description="Vehicle propulsion type (Electric, Hybrid, Gasoline)."
    )
    battery_capacity_kWh: Optional[float] = Field(
        default=None, description="Battery capacity if EV."
    )
    culinary_preferences: List[str] = Field(
        default_factory=list, description="User's dietary restrictions/preferences."
    )
    companion_preferences: List[str] = Field(
        default_factory=list,
        description="Additional dietary restrictions from companions.",
    )


class RoutePlannerInput(BaseModel):
    """Input contract for RoutePlannerAgent when called via AgentTool."""

    origin_city: str = Field(
        default="Milano",
        description="Origin city for the route (default 'Milano' if not specified).",
    )
    destination_city: str = Field(
        description="Final destination city (e.g., 'Roma', 'Firenze')."
    )


class SosteSearchInput(BaseModel):
    """Input contract for SosteSearchAgent when called via AgentTool."""

    latitude: float = Field(
        description="Target midpoint latitude returned by RoutePlannerAgent."
    )
    longitude: float = Field(
        description="Target midpoint longitude returned by RoutePlannerAgent."
    )
    fuel_type: str = Field(
        description="Canonical fuel/charging type ('ELECTRIC_FAST' for Electric vehicles, 'GASOLINE' for Gasoline/Hybrid, 'DIESEL' for Diesel)."
    )


class MenuCheckerInput(BaseModel):
    """Input contract for MenuCheckerAgent when called via AgentTool."""

    stop_names: List[str] = Field(
        description="Ordered list of highway stop_name strings returned by SosteSearchAgent."
    )
    dietary_preferences: List[str] = Field(
        description="List of dietary preferences to match (e.g., ['Vegan'])."
    )
