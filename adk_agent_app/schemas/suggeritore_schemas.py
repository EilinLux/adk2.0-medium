# agent/schemas/suggeritore_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class TripOptimizationRequest(BaseModel):
    """Input payload passed to Suggeritore to trigger the multi-agent optimization."""
    user_id: str = Field(description="Unique identifier for the user.")
    destination: str = Field(description="Final trip destination city or landmark.")
    vehicle_type: str = Field(description="Vehicle propulsion type (Electric, Hybrid, Gasoline).")
    battery_capacity_kWh: Optional[float] = Field(default=None, description="Battery capacity if EV.")
    culinary_preferences: List[str] = Field(default_factory=list, description="User's dietary restrictions/preferences.")
    companion_preferences: List[str] = Field(default_factory=list, description="Additional dietary restrictions from companions.")