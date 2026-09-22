# agent/schemas/user_schemas.py
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional

class UserRegistrationInput(BaseModel):
    """Input payload when calling the onboarding pipeline programmatically."""
    full_name: str = Field(description="Full legal or display name of the user.")
    email: str = Field(description="User's primary contact email address.")
    preferred_language: str = Field(default="English", description="Primary communication language.")
    culinary_preferences: List[str] = Field(default_factory=list, description="Dietary restrictions or food preferences.")
    vehicle_type: str = Field(default="Gasoline", description="Type of vehicle (Electric, Hybrid, Gasoline).")
    connector_type: Optional[str] = Field(default=None, description="EV charging plug type if applicable.")
    battery_capacity_kWh: Optional[float] = Field(default=None, description="Battery capacity in kWh if EV.")


class RegistrationSummaryOutput(BaseModel):
    """Output contract produced upon successful user registration."""
    status: str = Field(description="Registration status ('success' or 'failed').")
    user_id: str = Field(description="The unique system-generated User ID (e.g., 'usr_a1b2c3').")
    full_name: str = Field(description="Registered full name.")
    preferred_language: str = Field(description="Language configured for the profile.")
    profile_hydrated: bool = Field(description="True if profile state was successfully written to working memory.")