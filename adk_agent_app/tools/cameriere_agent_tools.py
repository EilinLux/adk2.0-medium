# adk_agent_app/tools/cameriere_agent_tools.py
from typing import Any, Dict, List
from google.cloud import firestore
from google.adk.tools import FunctionTool, ToolContext

from adk_agent_app.config import FIRESTORE_APP_DB, PROJECT_ID, logger


def _get_firestore_client() -> firestore.Client:
    """Lazy initializer to prevent gRPC fork / event loop conflicts."""
    return firestore.Client(project=PROJECT_ID, database=FIRESTORE_APP_DB)


async def extract_user_profile(user_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Extracts complete user profile from the Application DB and populates ADK Session Memory.
    """
    try:
        db = _get_firestore_client()
        doc = db.collection("users").document(user_id).get()

        if not doc.exists:
            return {"status": "error", "message": f"User '{user_id}' not found."}

        data = doc.to_dict() or {}
        vehicle = data.get("vehicle", {})

        # Hydrate all attributes into ADK Session Memory (user: scope)
        state = tool_context.state
        state["verified_user_id"] = user_id
        state["user:name"] = data.get("full_name")
        state["user:email"] = data.get("email")
        state["user:preferred_language"] = data.get("preferred_language", "English")
        state["user:culinary_preferences"] = data.get("culinary_preferences", [])
        state["user:vehicle_type"] = vehicle.get("vehicle_type", "Gasoline")
        state["user:connector_type"] = vehicle.get("connector_type")
        state["user:battery_capacity_kWh"] = vehicle.get("battery_capacity_kWh")
        state["user:account_status"] = data.get("account_status", "active")

        logger.info(f"Loaded complete profile for {user_id} into ADK session state.")

        return {
            "status": "success",
            "message": f"Session loaded for {data.get('full_name')}.",
            "profile": data,
        }
    except Exception as e:
        logger.error(f"Error loading session state: {e}", exc_info=True)
        return {"status": "error", "message": f"Session hydration failed: {str(e)}"}


async def update_dietary_preferences(
    new_preferences: List[str], tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Updates the user's culinary preferences across both active session memory
    and the primary Application Database (users collection).
    """
    try:
        # Retrieve verified user ID from session state (persisted across turns)
        user_id = (
            tool_context.state.get("verified_user_id")
            or tool_context.state.get("temp:verified_user_id")
            or tool_context.session.user_id
        )

        if not user_id:
            return {"status": "error", "message": "No active user ID found in session state."}

        clean_preferences = (
            [p.capitalize() for p in new_preferences]
            if isinstance(new_preferences, list)
            else [str(new_preferences).capitalize()]
        )

        # 1. Update active ADK Session State (immediate prompt injection availability)
        tool_context.state["user:culinary_preferences"] = clean_preferences

        # 2. Persist back to Primary Application Database (future logins)
        db = _get_firestore_client()
        db.collection("users").document(user_id).update(
            {"culinary_preferences": clean_preferences}
        )

        logger.info(
            f"Updated preferences for user '{user_id}' to {clean_preferences} in session state and App DB."
        )

        return {
            "status": "success",
            "message": f"Updated culinary preferences to {clean_preferences}.",
            "updated_preferences": clean_preferences,
        }
    except Exception as e:
        logger.error(f"Error updating dietary preferences: {e}", exc_info=True)
        return {"status": "error", "message": f"Failed to update preferences: {str(e)}"}


# Wrap as ADK FunctionTools
# Note: The tool name exposed to the LLM is `func.__name__`, not the Python variable name.
update_dietary_preferences_tool = FunctionTool(update_dietary_preferences)
extract_user_profile_tool = FunctionTool(extract_user_profile)
