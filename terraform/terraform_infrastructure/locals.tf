# ==========================================
# LOCAL VALUES FOR NAMING AND CONFIGURATION
# ==========================================
# Centralized naming conventions and shared values
# Ensures consistency across all resources

locals {
  # App naming
  app_name = "adk-agent"
  env_tag  = var.environment

  # Resource naming convention: {app_name}-{environment}-{resource}
  resource_prefix = "${local.app_name}-${local.env_tag}"

  # GCP Services to enable
  gcp_services = [
    "cloudresourcemanager.googleapis.com", # Resource management
    "compute.googleapis.com",              # Compute Engine (required for Cloud Run)
    "run.googleapis.com",                  # Cloud Run
    "artifactregistry.googleapis.com",     # Artifact Registry for Docker images
    "containerregistry.googleapis.com",    # Container Registry
    "cloudbuild.googleapis.com",           # Cloud Build
    "iam.googleapis.com",                  # IAM
    "iamcredentials.googleapis.com",       # IAM Credentials
    "serviceusage.googleapis.com",         # Service Usage
    "bigquery.googleapis.com",             # BigQuery
    "bigquerydatatransfer.googleapis.com", # BigQuery Data Transfer
    "firestore.googleapis.com",            # Firestore
    "aiplatform.googleapis.com",           # Vertex AI (for LLMs)
    "logging.googleapis.com",              # Cloud Logging
    "monitoring.googleapis.com",           # Cloud Monitoring
    "cloudtrace.googleapis.com",           # Cloud Trace
  ]

  # Common labels for all resources
  common_labels = {
    app         = local.app_name
    environment = local.env_tag
    managed_by  = "terraform"
  }

  # BigQuery configuration
  bigquery_config = {
    dataset_id       = var.bigquery_dataset_id
    dataset_location = var.bigquery_location
    table_id         = var.bigquery_table_id
  }

  # Firestore configuration
  firestore_config = {
    session_db_name     = "${local.resource_prefix}-session-memory-fs"
    food_kb_db_name     = "${local.resource_prefix}-food-kb-fs"
    application_db_name = "${local.resource_prefix}-application-db-fs"

    location = var.firestore_location
  }

  # Cloud Run configuration (3-Service Distributed Stack)
  cloud_run_config = {
    service_name             = local.resource_prefix
    mcp_service_name         = "${local.resource_prefix}-mcp-sse"
    suggeritore_service_name = "${local.resource_prefix}-suggeritore-a2a"
    min_instances            = var.cloud_run_min_instances
    max_instances            = var.cloud_run_max_instances
    memory                   = var.cloud_run_memory
    cpu                      = var.cloud_run_cpu
    timeout                  = var.cloud_run_timeout
  }
  # Bucket configuration
  product_specs_bucket_config = {
    name   = "${local.resource_prefix}-product-specs"
    region = var.bucket_region
  }
  # Service Account naming
  service_account_id = "${local.resource_prefix}-sa"
}
