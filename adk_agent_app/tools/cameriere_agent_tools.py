from adk_agent_app.config import logger, db
from google.adk.tools import FunctionTool
import uuid
from typing import List, Dict, Any

# ==========================================
# 1. CORE FUNCTIONS WITH ERROR HANDLING
# ==========================================

def extract_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Use this tool to retrieve a registered user's saved dietary preferences and vehicle type.
    Trigger this when you need to know the historical profile of an existing user.
    
    Args:
        user_id (str): The unique identifier of the registered user.
        
    Returns:
        Dict: Contains 'status' ("success" or "error"). If success, includes a 'data' dictionary 
              with 'culinary_preferences' (List[str]) and 'vehicle_type' (str).
    """
    try:
        # Check if the user ID exists in the mock dictionary
        if user_id in db:
            data = db[user_id]
            return {
                "status": "success",
                "data": {
                    "culinary_preferences": data.get("culinary_preferences", []),
                    "vehicle_type": data.get("vehicle_type", "Sconosciuto")
                },
                "message": "User profile extracted successfully."
            }
        else:
            return {
                "status": "error",
                "message": f"Cannot extract profile. User ID '{user_id}' was not found in the database."
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
