# ==========================================
# OUTPUT VALUES
# ==========================================
# Expose important resource information for use in other systems


# ==========================================
# CLOUD RUN OUTPUTS
# ==========================================

# output "cloud_run_service_url" {
#   description = "The URL of the Cloud Run service"
#   value       = google_cloud_run_service.adk_agent.status[0].url
# }

# output "cloud_run_service_name" {
#   description = "The name of the Cloud Run service"
#   value       = google_cloud_run_service.adk_agent.name
# }

# output "cloud_run_service_id" {
#   description = "The ID of the Cloud Run service"
#   value       = google_cloud_run_service.adk_agent.id
# }

# output "cloud_run_latest_revision" {
#   description = "The latest revision of the Cloud Run service"
#   value       = google_cloud_run_service.adk_agent.status[0].latest_created_revision_name
#}


# ==========================================
# SERVICE ACCOUNT OUTPUTS
# ==========================================

output "service_account_email" {
  description = "Email of the service account used by Cloud Run"
  value       = google_service_account.adk_agent.email
}

output "service_account_id" {
  description = "The ID of the service account"
  value       = google_service_account.adk_agent.unique_id
}

output "service_account_name" {
  description = "The name of the service account"
  value       = google_service_account.adk_agent.account_id
}

# ==========================================
# BIGQUERY OUTPUTS
# ==========================================

output "bigquery_dataset_id" {
  description = "The ID of the BigQuery dataset"
  value       = google_bigquery_dataset.soste_app_dev.dataset_id
}

output "bigquery_dataset_project" {
  description = "The project containing the BigQuery dataset"
  value       = google_bigquery_dataset.soste_app_dev.project
}

output "bigquery_table_id" {
  description = "The ID of the BigQuery table"
  value       = google_bigquery_table.db_soste.table_id
}

output "bigquery_table_full_id" {
  description = "The fully qualified ID of the BigQuery table (project.dataset.table)"
  value       = "${google_bigquery_table.db_soste.project}.${google_bigquery_table.db_soste.dataset_id}.${google_bigquery_table.db_soste.table_id}"
}

# ==========================================
# FIRESTORE OUTPUTS
# ==========================================

output "firestore_session_database_name" {
  description = "Name of the Firestore session memory database"
  value       = google_firestore_database.adk_session_memory.name
}

output "firestore_session_database_uid" {
  description = "UID of the Firestore session memory database"
  value       = google_firestore_database.adk_session_memory.uid
}

output "firestore_food_kb_database_name" {
  description = "Name of the Firestore food knowledge base database"
  value       = google_firestore_database.food_knowledge_base.name
}

output "firestore_food_kb_database_uid" {
  description = "UID of the Firestore food knowledge base database"
  value       = google_firestore_database.food_knowledge_base.uid
}

# ==========================================
# GCP PROJECT INFORMATION
# ==========================================

output "gcp_project_id" {
  description = "The GCP project ID"
  value       = var.gcp_project
}

output "gcp_region" {
  description = "The GCP region"
  value       = var.gcp_region
}

output "environment" {
  description = "The deployment environment"
  value       = var.environment
}

# ==========================================
# DEPLOYMENT INFORMATION
#==========================================

# output "deployment_summary" {
#   description = "Summary of the deployed infrastructure"
#  value = {
#     service_name     = google_cloud_run_service.adk_agent.name
#   service_url      = google_cloud_run_service.adk_agent.status[0].url
#   service_account  = google_service_account.adk_agent.email
#   bigquery_table   = "${google_bigquery_table.db_soste.project}.${google_bigquery_table.db_soste.dataset_id}.${google_bigquery_table.db_soste.table_id}"
#   firestore_dbs    = [
#     google_firestore_database.adk_session_memory.name,
#     google_firestore_database.food_knowledge_base.name
#   ]
#   region = var.gcp_region
#   environment = var.environment
# }
# }

# ==========================================
# AUTHENTICATION INFORMATION
# ==========================================

output "authentication_info" {
  description = "Information needed for authentication and configuration"
  value = {
    service_account_email = google_service_account.adk_agent.email
    service_account_id    = google_service_account.adk_agent.unique_id
    gcp_project           = var.gcp_project
    #cloud_run_url         = google_cloud_run_service.adk_agent.status[0].url
    requires_authentication = var.require_authentication
  }
}

# ==========================================
# MONITORING ENDPOINTS
# ==========================================

#output "cloud_run_metrics_dashboard" {
#description = "URL to Cloud Run metrics dashboard"
#value       = "https://console.cloud.google.com/run/detail/${var.gcp_region}/${google_cloud_run_service.adk_agent.name}/metrics"
#}

#output "cloud_run_logs_url" {
#description = "URL to Cloud Run logs in Cloud Logging"
#value       = "https://console.cloud.google.com/logs/query;query=resource.type=%22cloud_run_revision%22%20resource.labels.service_name=%22${google_cloud_run_service.adk_agent.name}%22?project=${var.gcp_project}"
#}

output "bigquery_console_url" {
  description = "URL to BigQuery dataset in Cloud Console"
  value       = "https://console.cloud.google.com/bigquery?project=${var.gcp_project}&p=${var.gcp_project}&d=${google_bigquery_dataset.soste_app_dev.dataset_id}"
}

output "product_specs_bucket_name" {
  description = "The name of the GCS bucket storing product PDF specification sheets."
  value       = google_storage_bucket.product_specs_bucket.name
}

output "product_specs_bucket_url" {
  description = "The gs:// URI of the product specification bucket."
  value       = "gs://${google_storage_bucket.product_specs_bucket.name}"
}