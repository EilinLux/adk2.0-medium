import os
from dotenv import load_dotenv
from google.cloud import firestore

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "adk-workshop-sosta-app-dev")
DATABASE_ID = os.getenv("FIRESTORE_APP_DB", "adk-agent-dev-application-db-fs")
COLLECTION_NAME = "users"

print(f"Connecting to Firestore database '{DATABASE_ID}'...")

# Initialize the Firestore client targeting the specific database
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

# ==========================================
# MOCK DATA (TRANSLATED)
# ==========================================
# Using the stop name as the Document ID for direct lookups
mock_users = {
    "usr_12345": {
        "full_name": "Alice Smith",
        "email": "alice@example.com",
        "preferred_language": "Italian",
        "culinary_preferences": ["Vegetarian", "Nut-free"],
        "vehicle": {
            "vehicle_type": "Electric",
            "connector_type": "CCS2",
            "battery_capacity_kWh": 77
        },
        "account_status": "active"
    },
    "usr_67890": {
        "full_name": "Bob Jones",
        "email": "bob@example.com",
        "preferred_language": "English",
        "culinary_preferences": ["Gluten-free"],
        "vehicle": {
            "vehicle_type": "Gasoline",
            "connector_type": None,
            "battery_capacity_kWh": None
        },
        "account_status": "active"
    },
    "usr_55555": {
        "full_name": "Carla Rossi",
        "email": "carla@example.com",
        "preferred_language": "Italian",
        "culinary_preferences": ["Vegan", "Halal"],
        "vehicle": {
            "vehicle_type": "Electric",
            "connector_type": "Type 2",
            "battery_capacity_kWh": 52
        },
        "account_status": "active"
    },
    "usr_0a8f67": {
        "user_id": "usr_0a8f67",
        "full_name": "Zelda Ailine Luconi",
        "email": "zelda.luconi@gmail.com",
        "preferred_language": "Italian",
        "culinary_preferences": ["Vegan"],
        "vehicle": {
            "vehicle_type": "Electric",
            "connector_type": None,
            "battery_capacity_kWh": None
        },
        "account_status": "active",
        "created_at": "2026-09-11T13:37:44.114983Z"
    }
}

# ==========================================
# EXECUTION
# ==========================================
def seed_database():
    print(f"Populating collection '{COLLECTION_NAME}'...")
    
    # Get a reference to the collection
    collection_ref = db.collection(COLLECTION_NAME)
    
    success_count = 0
    for user_id, data in mock_users.items():
        try:
            # Using the user_id as the Document ID
            doc_ref = collection_ref.document(user_id)
            
            # Prepare payload
            payload = {
                "user_id": user_id,
                "full_name": data["full_name"],
                "email": data["email"],
                "preferred_language": data["preferred_language"],
                "culinary_preferences": data["culinary_preferences"],
                "vehicle": data["vehicle"],
                "account_status": data["account_status"]
            }
            if "created_at" in data:
                payload["created_at"] = data["created_at"]
            
            doc_ref.set(payload)
            print(f"  -> Inserted data for: {user_id}")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Failed to insert data for {user_id}: {e}")
            
    print(f"✅ Successfully seeded {success_count} documents into Firestore!")

if __name__ == "__main__":
    seed_database()