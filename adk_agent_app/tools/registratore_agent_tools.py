from adk_agent_app.config import logger, db
from google.adk.tools import FunctionTool
import uuid
from typing import List, Dict, Any

# ==========================================
# 1. CORE FUNCTIONS WITH ERROR HANDLING
# ==========================================

def save_new_user(culinary_preferences: List[str], vehicle_type: str) -> Dict[str, Any]:
    """
    Use this tool to register a brand new user into the database and generate their unique ID.
    Trigger this only after asking the user for both their food preferences and vehicle type.
    
    Args:
        culinary_preferences (List[str]): Dietary preferences (e.g., ["Vegan", "gluten-free"]).
        vehicle_type (str): Vehicle type (e.g., 'Gasoline', 'Diesel', 'Electric').
        
    Returns:
        Dict: Contains 'status' ("success" or "error"), the new 'user_id' if successful, and a 'message'.
    """
    try:
        new_id = f"usr_{uuid.uuid4().hex[:5]}"
        
        # Save directly to the mock dictionary
        db[new_id] = {
            "culinary_preferences": culinary_preferences,
            "vehicle_type": vehicle_type
        }
        
        logger.info(f"Saved new user {new_id} to mock database.")
        return {
            "status": "success",
            "user_id": new_id,
            "message": "User registered successfully. Please provide this user ID to the user."
        }
    except Exception as e:
        logger.error(f"Error in save_new_user: {e}")
        return {
            "status": "error",
            "message": f"Failed to save the new user to the database due to an error: {str(e)}"
        }

# ==========================================
# 2. WRAP FUNCTIONS AS FUNCTION TOOLS
# ========================================== 
save_new_user_tool = FunctionTool(save_new_user)