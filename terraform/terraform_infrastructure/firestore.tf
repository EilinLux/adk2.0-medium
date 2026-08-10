# ==========================================
# FIRESTORE DATABASE - SESSION MEMORY
# ==========================================
# Stores ADK session state, context, and agent memory
# Multiple agents (Gatekeeper, Cameriere, Suggeritore) share this database

resource "google_firestore_database" "adk_session_memory" {
  provider    = google-beta
  project     = var.gcp_project
  name        = local.firestore_config.session_db_name
  location_id = local.firestore_config.location
  type        = "FIRESTORE_NATIVE"

  # Deletion policy: SOFT_DELETE for production safety
  # Change to SOFT_DELETE in prod (requires running `gcloud firestore delete-database`)
  deletion_policy = var.environment == "prod" && var.firestore_delete_protection ? "SOFT_DELETE" : "DELETE"

  depends_on = [google_project_service.required_apis]
}

# ==========================================
# FIRESTORE DATABASE - FOOD KNOWLEDGE BASE
# ==========================================
# Stores food data, recipes, ingredients, and nutritional information
# Used by the Suggeritore agent for food recommendations

resource "google_firestore_database" "food_knowledge_base" {
  provider    = google-beta
  project     = var.gcp_project
  name        = local.firestore_config.food_kb_db_name
  location_id = local.firestore_config.location
  type        = "FIRESTORE_NATIVE"

  deletion_policy = var.environment == "prod" && var.firestore_delete_protection ? "SOFT_DELETE" : "DELETE"

  depends_on = [google_project_service.required_apis]
}

# ==========================================
# FIRESTORE INDEXES
# ==========================================
# Define composite indexes for efficient Firestore queries

resource "google_firestore_index" "session_memory_user_timestamp" {
  provider   = google-beta
  project    = var.gcp_project
  database   = google_firestore_database.adk_session_memory.name
  collection = "sessions"

  fields {
    field_path = "user_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "created_at"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "food_kb_category_rating" {
  provider   = google-beta
  project    = var.gcp_project
  database   = google_firestore_database.food_knowledge_base.name
  collection = "foods"

  fields {
    field_path = "category"
    order      = "ASCENDING"
  }

  fields {
    field_path = "rating"
    order      = "DESCENDING"
  }
}

# ==========================================
# FIRESTORE SECURITY RULES
# ==========================================
# WARNING: Default rules allow anyone to read/write. Set up proper security rules!
# See: https://firebase.google.com/docs/firestore/security/get-started

# To deploy Firestore security rules:
# 1. Create a firestore-security-rules.txt file with your rules
# 2. Use: gcloud firestore indexes create -r firestore-security-rules.txt
#
# Or use the Firebase CLI:
# 1. npm install -g firebase-tools
# 2. firebase login
# 3. firebase deploy --only firestore:rules

# ==========================================
# IAM BINDINGS (Project-level for Firestore)
# ==========================================
# Note: Firestore IAM is managed at the project level, not database level
# The service account needs datastore.user role (already granted via project-level IAM)
