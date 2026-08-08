import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()  # Load .env file 

# ==========================================
# 0. SETUP & DATABASE INITIALIZATION
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Mock database initialized with schema matching the tools
db = {
    "usr_12345": {
        "name": "Alice", 
        "email": "alice@example.com",
        "culinary_preferences": ["Vegetarian", "Nut-free"],
        "vehicle_type": "Electric"
    },
    "usr_67890": {
        "name": "Bob", 
        "email": "bob@example.com",
        "culinary_preferences": ["Gluten-free"],
        "vehicle_type": "Gasoline"
    }
}