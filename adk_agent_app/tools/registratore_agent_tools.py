# agent/tools/registratore_agent_tools.py
import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from google.cloud import firestore
from google.adk.tools import FunctionTool

from ..config import logger
import dotenv

dotenv.load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT", "adk-workshop-sosta-app-dev")
APPLICATION_DB_NAME = os.getenv("APPLICATION_DB_NAME", "adk-agent-dev-application-db-dev-fs")

def _get_firestore_client():
    return firestore.Client(project=PROJECT_ID, database=APPLICATION_DB_NAME)

import os, uuid
import hashlib

def get_user_id(email: str) -> str:
  if os.getenv("ADK_EVAL_MODE") == "true":
    # Returns a deterministic hash based on email (e.g., 'usr_f93207' for Zelda, 'usr_ee1d9f' for Flora)
    clean_email = email.strip().lower()
    email_hash = hashlib.md5(clean_email.encode()).hexdigest()[:6]
    return f"usr_{email_hash}"

  return f"usr_{uuid.uuid4().hex[:6]}"

def save_new_user(
    full_name: str,
    email: str,
    preferred_language: str,
    culinary_preferences: List[str],
    vehicle_type: str,
    connector_type: Optional[str] = None,
    battery_capacity_kWh: Optional[float] = None
) -> Dict[str, Any]:
    """
    Registers a new user in the Application Database with complete profile details.
    """
    try:
        db = _get_firestore_client()
        new_id = get_user_id(email=email)
        
        clean_preferences = [p.capitalize() for p in culinary_preferences] if isinstance(culinary_preferences, list) else [str(culinary_preferences).capitalize()]
        clean_vehicle = vehicle_type.capitalize()

        user_payload = {
            "user_id": new_id,
            "full_name": full_name,
            "email": email,
            "preferred_language": preferred_language.capitalize(),
            "culinary_preferences": clean_preferences,
            "vehicle": {
                "vehicle_type": clean_vehicle,
                "connector_type": connector_type,
                "battery_capacity_kWh": battery_capacity_kWh
            },
            "account_status": "active",
            "created_at": datetime.now(timezone.utc)
        }

        # Save to primary Application DB
        db.collection("users").document(new_id).set(user_payload)
        logger.info(f"Registered user '{full_name}' ({new_id}) in Application DB.")

        return {
            "status": "success",
            "user_id": new_id,
            "message": f"Successfully registered {full_name} with ID '{new_id}'."
        }
    except Exception as e:
        logger.error(f"Error in save_new_user: {e}", exc_info=True)
        return {"status": "error", "message": f"Registration failed: {str(e)}"}

save_new_user_tool = FunctionTool(save_new_user)