# agent/tools/gatekeeper_tools.py
from adk_agent_app.config import logger
from typing import Dict, Any
from google.cloud import firestore
from google.adk.tools import FunctionTool
import os
PROJECT_ID = os.getenv("GCP_PROJECT", "adk-workshop-sosta-app-dev")
DATABASE_ID = "adk-session-memory"

# Always pass both project and database explicitly
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

# ==========================================
# 1. CORE FUNCTIONS WITH ERROR HANDLING
# ==========================================

def extract_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Retrieves a registered user's saved dietary preferences, vehicle type, 
    and general profile details directly from Firestore.
    Trigger this when you need to know the historical profile of an existing user.
    
    Args:
        user_id (str): The unique identifier of the registered user (e.g., 'user_9876').
        
    Returns:
        Dict: Contains 'status' ("success" or "error"). If success, includes a 'data' dictionary 
              with 'culinary_preferences' (List[str]), 'vehicle_type' (str), and optional metadata.
    """
    try:
        # 1. Fetch the user document from the 'users' collection in Firestore
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        # 2. Return error if document does not exist
        if not user_doc.exists:
            return {
                "status": "error",
                "message": f"Cannot extract profile. User ID '{user_id}' was not found in Firestore."
            }

        data = user_doc.to_dict()

        # 3. Extract profile details safely
        return {
            "status": "success",
            "data": {
                "name": data.get("name", "Unknown"),
                "culinary_preferences": data.get("culinary_preferences", []),
                "vehicle_type": data.get("vehicle_type", "Sconosciuto"),
                "favorite_station": data.get("favorite_station", "None")
            },
            "message": f"User profile for '{user_id}' extracted successfully from Firestore."
        }

    except Exception as e:
        logger.error(f"Error in extract_user_profile: {e}")
        return {
            "status": "error",
            "message": f"Database error while extracting profile: {str(e)}"
        }

# ==========================================
# 2. WRAP FUNCTIONS AS FUNCTION TOOLS
# ========================================== 

extract_user_profile_tool = FunctionTool(extract_user_profile)