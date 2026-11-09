# adk_agent_app/tools/gatekeeper_tools.py
from typing import Any, Dict
from google.cloud import firestore
from google.adk.tools import FunctionTool, ToolContext

from ..config import FIRESTORE_APP_DB, PROJECT_ID, logger


def _get_firestore_client() -> firestore.Client:
    """Lazy initializer to prevent gRPC fork / event loop conflicts."""
    return firestore.Client(project=PROJECT_ID, database=FIRESTORE_APP_DB)


async def is_registered_user(user_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Verifies a user in the Application DB and records verified_user_id in session state.
    Full profile hydration is delegated exclusively to Cameriere's extract_user_profile tool upon transfer.
    """
    try:
        db = _get_firestore_client()
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return {
                "status": "not_found",
                "exists": False,
                "message": f"User ID '{user_id}' does not exist. Please ask the user if they would like to register.",
            }

        # Save verified ID key in session scope (for multi-turn tools) and temp: scope
        state = tool_context.state
        state["verified_user_id"] = user_id
        state["temp:verified_user_id"] = user_id
        state["workflow_step"] = "user_verified"

        logger.info(
            f"Verified user '{user_id}' successfully in Gatekeeper. Delegating profile hydration to Cameriere."
        )

        return {
            "status": "success",
            "exists": True,
            "verified_user_id": user_id,
            "message": f"User '{user_id}' verified successfully. Profile hydration delegated to Cameriere.",
        }

    except Exception as e:
        logger.error(f"Error in is_registered_user: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"A database error occurred while verifying the user: {str(e)}",
        }


# Note: When ADK generates the tool schema from FunctionTool(func),
# the tool name exposed to the LLM is `func.__name__` ('is_registered_user'),
# not the Python variable name ('is_registered_user_tool').
is_registered_user_tool = FunctionTool(is_registered_user)
