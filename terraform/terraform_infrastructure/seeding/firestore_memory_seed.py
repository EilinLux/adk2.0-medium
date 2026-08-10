import os
from google.cloud import firestore

# ==========================================
# CONFIGURATION
# ==========================================
PROJECT_ID = "adk-workshop-sosta-app-dev"
DATABASE_ID = "adk-agent-dev-session-memory-fs"
COLLECTION_NAME = "users"

print(f"Connecting to Firestore database '{DATABASE_ID}'...")
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

# ==========================================
# MOCK USER DATA
# ==========================================
mock_users = {
    "user_9876": {
        "name": "Zelda Luconi",
        "email": "zelda.luconi@example.com",
        "culinary_preferences": ["Vegetarian", "Gluten-Free"],
        "vehicle_type": "Electric",
        "favorite_station": "Autogrill Secchia Ovest"
    },
    "user_5432": {
        "name": "Marco Rossi",
        "email": "marco.rossi@example.com",
        "culinary_preferences": ["Lactose-Free", "High-Protein"],
        "vehicle_type": "Diesel",
        "favorite_station": "Autogrill Villoresi Est"
    },
    "user_1122": {
        "name": "Giulia Bianchi",
        "email": "giulia.bianchi@example.com",
        "culinary_preferences": ["Vegan"],
        "vehicle_type": "Gasoline",
        "favorite_station": "Autogrill Flaminia Est"
    },
    "user_3344": {
        "name": "Alessandro Moretti",
        "email": "alessandro.moretti@example.com",
        "culinary_preferences": ["Nut-Free", "Halal"],
        "vehicle_type": "LPG",
        "favorite_station": "Area di Servizio Cantagallo"
    }
}

# ==========================================
# EXECUTION
# ==========================================
def seed_users():
    print(f"Populating user profiles into collection '{COLLECTION_NAME}'...")
    collection_ref = db.collection(COLLECTION_NAME)
    success_count = 0

    for user_id, user_data in mock_users.items():
        try:
            doc_ref = collection_ref.document(user_id)
            payload = {
                "user_id": user_id,
                **user_data
            }
            doc_ref.set(payload)
            print(f"  -> Successfully registered user document: {user_id}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ Failed to seed user {user_id}: {e}")

    print(f"✅ Successfully seeded {success_count} user document(s) into Firestore!")

if __name__ == "__main__":
    seed_users()