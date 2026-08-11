# adk_agent_app/tools/registratore_agent_tools.py
from datetime import datetime, timezone
import hashlib
import os
from typing import Any, Dict, List, Optional
import uuid

from google.adk.tools import FunctionTool, ToolContext
from google.cloud import firestore

from ..config import FIRESTORE_APP_DB, PROJECT_ID, logger


def _get_firestore_client() -> firestore.Client:
    """Lazy initializer to prevent gRPC fork and event loop conflicts."""
    return firestore.Client(project=PROJECT_ID, database=FIRESTORE_APP_DB)


def get_user_id(email: str) -> str:
    """Generates a deterministic user ID during evaluation mode or a unique random ID in production.

    Args:
        email: The user's email address used to compute the evaluation hash.

    Returns:
        str: A formatted user ID string (e.g., 'usr_7c0adf' for zelda.luconi@gmail.com,
        'usr_ba7db8' for f.rossi@gmail.com).
    """
    if os.getenv("ADK_EVAL_MODE") == "true":
        clean_email = email.strip().lower()
        email_hash = hashlib.md5(clean_email.encode()).hexdigest()[:6]
        return f"usr_{email_hash}"

    return f"usr_{uuid.uuid4().hex[:6]}"


async def save_new_user(
    full_name: str,
    email: str,
    preferred_language: str,
    culinary_preferences: List[str],
    vehicle_type: str,
    tool_context: ToolContext,
    connector_type: Optional[str] = None,
    battery_capacity_kWh: Optional[float] = None,
) -> Dict[str, Any]:
    """Registers a new user profile in Firestore and hydrates active session memory.

    Use this tool when a user explicitly agrees to register, providing their personal details,
    food preferences, and vehicle specifications.
    Do NOT use this tool for existing users or to perform profile updates.

    Args:
        full_name: The complete name of the user (e.g., 'John Doe').
        email: A valid user email address (e.g., 'john.doe@example.com').
        preferred_language: The preferred language for communication (e.g., 'English', 'Italian').
        culinary_preferences: A list of food restrictions or preferences (e.g., ['Vegetarian', 'Nut-free']).
        vehicle_type: Type of vehicle driven (e.g., 'Electric', 'Hybrid', 'Gasoline').
        tool_context: Injected runtime context (automatically handled by ADK framework).
        connector_type: Optional EV plug specification (e.g., 'Type 2', 'CCS2').
        battery_capacity_kWh: Optional total battery size in kilowatt-hours (e.g., 75.5).

    Returns:
        Dict[str, Any]: A structured registration result dictionary.
            - status (str): Outcome of the operation ('success' or 'error').
            - user_id (str, optional): The newly assigned unique User ID.
            - message (str): Human-readable confirmation or failure explanation.
    """
    try:
        # Input validation
        if not full_name or not email:
            return {
                "status": "error",
                "message": "Missing required fields: Both 'full_name' and 'email' must be provided.",
            }

        db = _get_firestore_client()
        new_id = get_user_id(email=email)

        # Normalize culinary preferences into a clean list
        if isinstance(culinary_preferences, list):
            clean_preferences = [
                str(p).strip().capitalize() if str(p).strip() != "No specific preferences" else "No specific preferences"
                for p in culinary_preferences
                if str(p).strip()
            ]
        elif isinstance(culinary_preferences, str):
            clean_preferences = [culinary_preferences.strip().capitalize()]
        else:
            clean_preferences = []

        clean_vehicle_type = (
            vehicle_type.strip().capitalize() if vehicle_type else "Gasoline"
        )
        clean_language = (
            preferred_language.strip().capitalize() if preferred_language else "English"
        )
        created_at_iso = datetime.now(timezone.utc).isoformat()

        user_payload = {
            "user_id": new_id,
            "full_name": full_name.strip(),
            "email": email.strip().lower(),
            "preferred_language": clean_language,
            "culinary_preferences": clean_preferences,
            "vehicle": {
                "vehicle_type": clean_vehicle_type,
                "connector_type": connector_type or "",
                "battery_capacity_kWh": battery_capacity_kWh,
            },
            "account_status": "active",
            "created_at": created_at_iso,
        }

        # 1. Save to primary Application DB
        db.collection("users").document(new_id).set(user_payload)

        # 2. Hydrate active session memory via ToolContext so downstream agents can access it immediately
        state = tool_context.state
        state["verified_user_id"] = new_id
        state["user:name"] = full_name.strip()
        state["user:email"] = email.strip().lower()
        state["user:preferred_language"] = clean_language
        state["user:culinary_preferences"] = clean_preferences
        state["user:vehicle_type"] = clean_vehicle_type
        state["user:connector_type"] = connector_type or ""
        state["user:battery_capacity_kWh"] = battery_capacity_kWh
        state["temp:verified_user_id"] = new_id
        state["workflow_step"] = "user_registered"

        logger.info(
            f"Successfully registered user '{full_name}' ({new_id}) and hydrated session memory."
        )

        return {
            "status": "success",
            "user_id": new_id,
            "message": f"User '{full_name}' registered successfully with assigned User ID '{new_id}'.",
        }

    except Exception as e:
        logger.error(f"Error during save_new_user execution: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Registration failed due to a database exception: {str(e)}",
        }


# Wrap as an ADK FunctionTool instance
# Note: The tool name exposed to the LLM is `func.__name__` ('save_new_user'),
# not the Python variable name ('save_new_user_tool').
save_new_user_tool = FunctionTool(save_new_user)