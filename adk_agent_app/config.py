# adk_agent_app/config.py
import logging
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

# ==========================================
# 0. LOGGING & ENVIRONMENT CONFIGURATION
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = (
    os.getenv("GOOGLE_CLOUD_PROJECT")
    or os.getenv("GCP_PROJECT")
    or "adk-workshop-sosta-app-dev"
)
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Database Identifiers owned by the primary SostaApp agent (Gatekeeper / Registratore / Cameriere)
FIRESTORE_APP_DB = os.getenv("FIRESTORE_APP_DB", "adk-agent-dev-application-db-fs")
FIRESTORE_SESSION_DB = os.getenv("FIRESTORE_SESSION_DB", "adk-agent-dev-session-memory-fs")
