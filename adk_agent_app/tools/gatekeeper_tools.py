# agent/tools/gatekeeper_tools.py
import os
import uuid
from typing import Dict, Any
from datetime import datetime, timezone
from google.cloud import firestore
from google.adk.tools import FunctionTool
from adk_agent_app.config import logger

PROJECT_ID = os.getenv("GCP_PROJECT", "adk-workshop-sosta-app-dev")
DATABASE_ID = "adk-agent-dev-session-memory-fs"

db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

# ==========================================
# CORE FUNCTIONS WITH ERROR HANDLING
# ==========================================

def is_registered_user(user_id: str, anon_session_id: str = "") -> Dict[str, Any]:
    """
    Verifies a user, terminates their anonymous session, and creates a brand-new
    authenticated session bound directly to their registered user_id.

    Args:
        user_id: The unique identifier of the user (e.g., 'user_1122').
        anon_session_id: The temporary anonymous session ID to close/clean up.

    Returns:
        Verification status, new session details, and agent transition payload.
    """
    try:
        # 1. Verify user existence in 'users' collection
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return {
                "status": "not_found",
                "exists": False,
                "message": f"User ID '{user_id}' does not exist. The user needs to register."
            }

        user_data = user_doc.to_dict()
        preferences = user_data.get("culinary_preferences", [])
        vehicle_type = user_data.get("vehicle_type", "Unknown")

        # 2. Generate a NEW session ID tied to the authenticated user
        new_session_id = f"sess_{user_id}_{uuid.uuid4().hex[:6]}"
        new_session_ref = db.collection("sessions").document(new_session_id)

        new_session_payload = {
            "session_id": new_session_id,
            "user_id": user_id,
            "is_authenticated": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "state": {
                "user:culinary_preferences": preferences,
                "user:vehicle_type": vehicle_type,
                "user:name": user_data.get("name", "")
            }
        }
        
        # Write the new session under the user_id context
        new_session_ref.set(new_session_payload)
        logger.info(f"Created new authenticated session '{new_session_id}' for user '{user_id}'.")

        # 3. Clean up the anonymous session if provided
        if anon_session_id and anon_session_id != new_session_id:
            try:
                db.collection("sessions").document(anon_session_id).delete()
                logger.info(f"Cleaned up temporary anonymous session '{anon_session_id}'.")
            except Exception as del_err:
                logger.warning(f"Failed to remove temp session '{anon_session_id}': {del_err}")

        return {
            "status": "success",
            "exists": True,
            "verified_user_id": user_id,
            "new_session_id": new_session_id,
            "message": (
                f"User '{user_id}' verified successfully. Created new authenticated session "
                f"'{new_session_id}' with preferences: {preferences}"
            )
        }

    except Exception as e:
        logger.error(f"Error in is_registered_user: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"A database error occurred while creating user session: {str(e)}"
        }

# ==========================================
# WRAP FUNCTION AS ADK TOOL
# ==========================================
is_registered_user_tool = FunctionTool(is_registered_user)