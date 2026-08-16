# ==========================================
# GOOGLE CLOUD MEMORYSTORE FOR REDIS (OPTIONAL)
# ==========================================
# Provides a managed in-memory cache for tool responses and shared session state.
# Enables sub-millisecond retrieval of BigQuery geospatial queries and Firestore lookups.
# Controlled via var.enable_memorystore_redis (defaults to false for dev cost optimization).

resource "google_redis_instance" "cache" {
  count          = var.enable_memorystore_redis ? 1 : 0
  name           = "${local.resource_prefix}-redis"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_size_gb
  region         = var.gcp_region
  project        = var.gcp_project

  redis_version = "REDIS_7_0"
  display_name  = "ADK Tool Caching Memorystore (${var.environment})"
  labels        = local.common_labels

  # Maintenance window (Sunday early morning UTC)
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 2
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }

  depends_on = [
    google_project_service.required_apis
  ]
}
