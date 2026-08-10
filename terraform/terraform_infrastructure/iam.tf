# ==========================================
# SERVICE ACCOUNT
# ==========================================
# Service account for Cloud Run service to authenticate with GCP services

resource "google_service_account" "adk_agent" {
  project      = var.gcp_project
  account_id   = local.service_account_id
  display_name = var.service_account_display_name
  description  = "Service account for ${var.app_display_name} in ${var.environment} environment"
}

# ==========================================
# IAM ROLES - CLOUD RUN
# ==========================================
# Minimal permissions for Cloud Run to function

resource "google_project_iam_member" "cloud_run_service_agent" {
  project = var.gcp_project
  role    = "roles/run.serviceAgent"
  member  = "serviceAccount:${google_service_account.adk_agent.email}"
}

# ==========================================
# IAM ROLES - BIGQUERY
# ==========================================
# Permissions for the service account to read/write to BigQuery

resource "google_project_iam_member" "bigquery_editor" {
  project = var.gcp_project
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.adk_agent.email}"
}

resource "google_project_iam_member" "bigquery_job_user" {
  project = var.gcp_project
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.adk_agent.email}"
}

# ==========================================
# IAM ROLES - FIRESTORE
# ==========================================
# Permissions for the service account to access Firestore databases

resource "google_project_iam_member" "firestore_user" {
  project = var.gcp_project
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.adk_agent.email}"
}

# ==========================================
# IAM ROLES - BUCKET
# ==========================================
# Permissions for the service account to access Cloud Storage buckets

resource "google_storage_bucket_iam_member" "agent_pdf_reader" {
  bucket = google_storage_bucket.product_specs_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.adk_agent.email}"
} 


# ==========================================
# IAM ROLES - VERTEX AI & ML
# ==========================================
# Permissions for the service account to use Vertex AI LLMs

resource "google_project_iam_member" "vertex_ai_user" {
  project = var.gcp_project
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.adk_agent.email}"
}

# ==========================================
# IAM ROLES - LOGGING & MONITORING
# ==========================================
# Permissions for the service account to write logs and metrics

resource "google_project_iam_member" "logging_log_writer" {
  project = var.gcp_project
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.adk_agent.email}"
}

resource "google_project_iam_member" "monitoring_metric_writer" {
  project = var.gcp_project
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.adk_agent.email}"
}

resource "google_project_iam_member" "cloudtrace_agent" {
  project = var.gcp_project
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.adk_agent.email}"
}

# ==========================================
# IAM ROLES - ARTIFACT REGISTRY
# ==========================================
# Permissions to pull container images from Artifact Registry

resource "google_project_iam_member" "artifact_registry_reader" {
  project = var.gcp_project
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.adk_agent.email}"
}

# ==========================================
# CUSTOM ROLES (OPTIONAL)
# ==========================================
# Uncomment to grant additional roles if needed

# Example: Grant Cloud Build Editor for CI/CD
# resource "google_project_iam_member" "cloud_build_editor" {
#   project = var.gcp_project
#   role    = "roles/cloudbuild.builds.editor"
#   member  = "serviceAccount:${google_service_account.adk_agent.email}"
# }

# ==========================================
# EXTRA ROLES FROM VARIABLE
# ==========================================
# Allow users to specify additional roles if needed

resource "google_project_iam_member" "extra_roles" {
  for_each = toset(var.service_account_extra_roles)

  project = var.gcp_project
  role    = each.value
  member  = "serviceAccount:${google_service_account.adk_agent.email}"
}

