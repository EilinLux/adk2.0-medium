# agent/tools/gatekeeper_tools.py
from adk_agent_app.config import logger, db
from typing import Dict, Any
from google.adk.tools import FunctionTool

  
# ==========================================
# 1. CORE FUNCTIONS WITH ERROR HANDLING
# ==========================================


def is_registered_user(user_id: str) -> Dict[str, Any]:
    """
    Checks the database to verify if a given User ID is registered.

    Args:
        user_id: The unique identifier of the user (e.g., 'usr_12345').

    Returns:
        A dictionary containing the verification status, existence flag, 
        and a descriptive message for the agent.
    """
    try:
        # Simulating a database check (e.g., db.collection("users").document(user_id).get())
        if user_id in db:
            return {
                "status": "success",
                "exists": True,
                "message": f"Success: User ID '{user_id}' was found in the database."
            }
        else:
            return {
                "status": "not_found",
                "exists": False,
                "message": f"User ID '{user_id}' does not exist. The user might need to register."
            }
            
    except Exception as e:
        logger.error(f"Error in is_registered_user_tool: {e}")
        return {
            "status": "error",
            "message": f"A database error occurred while verifying the user ID: {str(e)}"
        }

# ==========================================
# 2. WRAP FUNCTIONS AS FUNCTION TOOLS
# ==========================================

is_registered_user_tool = FunctionTool(is_registered_user)
