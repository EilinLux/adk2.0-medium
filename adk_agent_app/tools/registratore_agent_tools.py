# agent/tools/gatekeeper_tools.py
import os
import uuid
from typing import List, Dict, Any
from datetime import datetime, timezone
from google.cloud import firestore
from google.adk.tools import FunctionTool
from adk_agent_app.config import logger

PROJECT_ID = os.getenv("GCP_PROJECT", "adk-workshop-sosta-app-dev")
DATABASE_ID = "adk-agent-dev-session-memory-fs"

def _get_firestore_client():
    """Lazy initializer to prevent gRPC fork / event loop conflicts."""
    return firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

def save_new_user(
    name: str,
    culinary_preferences: List[str],
    vehicle_type: str,
    email: str = ""
) -> Dict[str, Any]:
    """
    Registers a new user in Firestore and generates a unique ID.
    
    Args:
        name: User's full name.
        culinary_preferences: Dietary preferences list (e.g., ['Vegan']).
        vehicle_type: Vehicle engine/charging type (e.g., 'Electric', 'Gasoline').
        email: Optional email address.
    """
    try:
        db = _get_firestore_client()
        new_id = f"user_{uuid.uuid4().hex[:4]}"
        
        # Standardize inputs
        clean_preferences = [p.capitalize() for p in culinary_preferences] if isinstance(culinary_preferences, list) else [str(culinary_preferences).capitalize()]
        clean_vehicle = vehicle_type.capitalize()

        user_payload = {
            "user_id": new_id,
            "name": name,
            "email": email,
            "culinary_preferences": clean_preferences,
            "vehicle_type": clean_vehicle,
            "created_at": datetime.now(timezone.utc)
        }

        # Write user profile to 'users' collection
        user_ref = db.collection("users").document(new_id)
        user_ref.set(user_payload)

        logger.info(f"Successfully registered user '{name}' with ID '{new_id}' in Firestore.")

        return {
            "status": "success",
            "user_id": new_id,
            "message": f"User '{name}' registered successfully with ID '{new_id}'. Please inform the user of their new User ID."
        }
    except Exception as e:
        logger.error(f"Error in save_new_user: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to complete user registration due to database error: {str(e)}"
        }

save_new_user_tool = FunctionTool(save_new_user)