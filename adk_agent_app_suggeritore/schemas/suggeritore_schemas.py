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


class TripCalculatorInput(BaseModel):
    """Input contract for TripCalculatorAgent when called via AgentTool."""

    battery_capacity_kwh: float = Field(
        description="Total EV battery capacity in kWh (e.g., 75.0)."
    )
    current_soc_percent: float = Field(
        default=20.0,
        description="Current battery State of Charge percentage on arrival (e.g., 20.0).",
    )
    target_soc_percent: float = Field(
        default=80.0,
        description="Target battery State of Charge percentage at departure (e.g., 80.0).",
    )
    charger_power_kw: float = Field(
        default=150.0,
        description="DC fast charger power output in kW (e.g., 150.0).",
    )
    cost_per_kwh_eur: float = Field(
        default=0.65,
        description="Unit price of electricity in EUR per kWh (default 0.65).",
    )
    dining_cost_eur: float = Field(
        default=0.0,
        description="Estimated total dining cost in EUR across all travelers (default 0.0).",
    )
    passengers_count: int = Field(
        default=1,
        description="Total number of travelers splitting the charging + dining bill (default 1).",
    )

