# agent/tools/gatekeeper_tools.py
import os
from typing import Dict, Any
from google.cloud import firestore
from google.adk.tools import ToolContext, FunctionTool

from ..config import logger
import dotenv

dotenv.load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT", "adk-workshop-sosta-app-dev")
APPLICATION_DB_NAME = os.getenv("APPLICATION_DB_NAME", "adk-agent-dev-application-db-dev-fs")

def _get_firestore_client():
    """Lazy initializer to prevent gRPC fork / event loop conflicts."""
    return firestore.Client(project=PROJECT_ID, database=APPLICATION_DB_NAME)


async def is_registered_user(user_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Verifies a user in the Application DB and hydrates their profile directly 
    into ADK Session Memory (user: scope) for immediate agent availability.
    """
    try:
        db = _get_firestore_client()
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return {
                "status": "not_found",
                "exists": False,
                "message": f"User ID '{user_id}' does not exist. Please ask the user if they would like to register."
            }

        user_data = user_doc.to_dict()
        vehicle = user_data.get("vehicle", {})

        # Hydrate active ADK Session Memory via ToolContext
        state = tool_context.session.state
        state["user:name"] = user_data.get("full_name") or user_data.get("name", "")
        state["user:email"] = user_data.get("email", "")
        state["user:preferred_language"] = user_data.get("preferred_language", "English")
        state["user:culinary_preferences"] = user_data.get("culinary_preferences", [])
        state["user:vehicle_type"] = vehicle.get("vehicle_type", user_data.get("vehicle_type", "Gasoline"))
        
        # Save temporary verified ID key for workflow routing
        state["temp:verified_user_id"] = user_id
        state["workflow_step"] = "user_verified"

        logger.info(f"Verified user '{user_id}' and hydrated profile into active ADK session memory.")

        return {
            "status": "success",
            "exists": True,
            "verified_user_id": user_id,
            "message": f"User '{user_id}' verified successfully. Profile loaded into working memory."
        }

    except Exception as e:
        logger.error(f"Error in is_registered_user: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"A database error occurred while verifying the user: {str(e)}"
        }


# Wrap as an ADK FunctionTool (accepts ToolContext automatically)
is_registered_user_tool = FunctionTool(is_registered_user)