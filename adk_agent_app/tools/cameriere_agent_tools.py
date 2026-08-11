# agent/tools/cameriere_agent_tools.py
import os
import dotenv
from typing import Dict, Any, List
from google.cloud import firestore
from google.adk.tools import ToolContext, FunctionTool

from ..config import logger

dotenv.load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT", "adk-workshop-sosta-app-dev")
APPLICATION_DB_NAME = os.getenv("APPLICATION_DB_NAME", "adk-agent-dev-application-db-dev-fs")


def _get_firestore_client() -> firestore.Client:
    """Lazy initializer to prevent gRPC fork and event loop conflicts."""
    return firestore.Client(project=PROJECT_ID, database=APPLICATION_DB_NAME)


async def extract_user_profile(user_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Retrieves a user profile from Firestore and hydrates active ADK session memory.

    Use this tool when a user logs in or provides their User ID to load their profile,
    preferences, and vehicle information into working memory.
    Do NOT use this tool to update existing information or search for unverified users.

    Args:
        user_id: The unique string identifier for the user (e.g., 'usr_12345').

    Returns:
        Dict[str, Any]: A structured status report containing profile data and state info.
            - status (str): Execution result ('success' or 'error').
            - message (str): Human-readable confirmation or error context.
            - profile (Dict[str, Any], optional): Full user document retrieved from database.
    """
    try:
        if not user_id or not isinstance(user_id, str):
            return {
                "status": "error",
                "message": "Invalid argument: 'user_id' must be a non-empty string."
            }

        db = _get_firestore_client()
        doc_ref = db.collection("users").document(user_id)
        doc = doc_ref.get()

        if not doc.exists:
            return {
                "status": "error",
                "message": f"User ID '{user_id}' was not found in the database."
            }

        data = doc.to_dict() or {}
        vehicle = data.get("vehicle", {})

        # Hydrate all attributes into active ADK Session Memory (user: scope)
        state = tool_context.session.state
        state["user:name"] = data.get("full_name") or data.get("name", "")
        state["user:email"] = data.get("email", "")
        state["user:preferred_language"] = data.get("preferred_language", "English")
        state["user:culinary_preferences"] = data.get("culinary_preferences", [])
        state["user:vehicle_type"] = vehicle.get("vehicle_type", "Gasoline")
        state["user:connector_type"] = vehicle.get("connector_type", "")
        state["user:battery_capacity_kWh"] = vehicle.get("battery_capacity_kWh")
        state["user:account_status"] = data.get("account_status", "active")

        # Track verified state
        state["temp:verified_user_id"] = user_id

        logger.info(f"Loaded complete profile for '{user_id}' into ADK session state.")

        return {
            "status": "success",
            "message": f"Session memory successfully hydrated for user '{data.get('full_name', user_id)}'.",
            "profile": data
        }

    except Exception as e:
        logger.error(f"Error in extract_user_profile for user '{user_id}': {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Database query failed while extracting user profile: {str(e)}"
        }


async def update_dietary_preferences(
    new_preferences: List[str], 
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Updates a user's culinary and dietary preferences in both session state and database.

    Use when the user explicitly requests to update, add, or change their food allergies,
    dietary restrictions, or culinary preferences (e.g., 'I am vegetarian', 'I dislike seafood').
    Do NOT use for general order placement or vehicle preferences.

    Args:
        new_preferences: A list of updated preference strings (e.g., ['Vegetarian', 'Nut-free']).

    Returns:
        Dict[str, Any]: Execution feedback detailing updated state.
            - status (str): Outcome of the operation ('success' or 'error').
            - message (str): Clear message suitable for informing the user.
            - updated_preferences (List[str], optional): The clean list of saved preferences.
    """
    try:
        # Retrieve verified user ID from session state or session user context
        user_id = (
            tool_context.session.state.get("temp:verified_user_id") 
            or tool_context.session.user_id
        )

        if not user_id:
            return {
                "status": "error",
                "message": "User verification required before updating preferences. Please identify the user first."
            }

        # Normalize preferences to clean list of capitalized strings
        if isinstance(new_preferences, list):
            clean_preferences = [str(p).strip().capitalize() for p in new_preferences if str(p).strip()]
        elif isinstance(new_preferences, str):
            clean_preferences = [new_preferences.strip().capitalize()]
        else:
            clean_preferences = []

        if not clean_preferences:
            return {
                "status": "error",
                "message": "No valid preferences provided. Please provide at least one dietary preference."
            }

        # 1. Update active ADK Session State
        tool_context.session.state["user:culinary_preferences"] = clean_preferences

        # 2. Persist to Firestore database
        db = _get_firestore_client()
        db.collection("users").document(user_id).update({
            "culinary_preferences": clean_preferences
        })

        logger.info(f"Updated preferences for user '{user_id}' to {clean_preferences} in session state and App DB.")

        return {
            "status": "success",
            "message": f"Successfully updated dietary preferences to: {', '.join(clean_preferences)}.",
            "updated_preferences": clean_preferences
        }

    except Exception as e:
        logger.error(f"Error in update_dietary_preferences: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to persist updated dietary preferences: {str(e)}"
        }


# Wrap raw Python functions as ADK FunctionTool instances
extract_user_profile_tool = FunctionTool(extract_user_profile)
update_dietary_preferences_tool = FunctionTool(update_dietary_preferences)