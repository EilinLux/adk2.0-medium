# ==========================================
# BIGQUERY DATASET
# ==========================================
# Dataset for storing application data from the ADK agent

resource "google_bigquery_dataset" "soste_app_dev" {
  dataset_id    = local.bigquery_config.dataset_id
  friendly_name = "Soste App Dataset"
  description   = "Dataset for the ${var.app_display_name} in ${var.environment} environment"
  location      = local.bigquery_config.dataset_location
  project       = var.gcp_project

  # Access control
  default_table_expiration_ms     = var.bigquery_table_expiration_days > 0 ? var.bigquery_table_expiration_days * 24 * 60 * 60 * 1000 : 0
  default_partition_expiration_ms = 0

  # Labels for resource management
  labels = local.common_labels

  # Allow the service account to access this dataset
  access {
    role          = "OWNER"
    user_by_email = google_service_account.adk_agent.email
  }

  access {
    role          = "READER"
    special_group = "projectReaders"
  }

  depends_on = [google_project_service.required_apis]
}

# ==========================================
# BIGQUERY TABLE - SERVICE STATIONS
# ==========================================
# Table schema for storing service station data with geographical information

resource "google_bigquery_table" "db_soste" {
  dataset_id = google_bigquery_dataset.soste_app_dev.dataset_id
  table_id   = local.bigquery_config.table_id
  project    = var.gcp_project

  friendly_name = "Service Stations Database"
  description   = "Stores service station locations with fuel types and geographical coordinates"

  labels = merge(
    local.common_labels,
    {
      data_type = "geographical"
      source    = "autogrill"
    }
  )

  # Define table schema
  schema = jsonencode([
    {
      name        = "autogrill_name"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Name of the service station"
    },
    {
      name        = "fuel_types"
      type        = "STRING"
      mode        = "REPEATED"
      description = "Array of available fuel and charging types (e.g., GASOLINE, DIESEL, ELECTRIC)"
    },
    {
      name        = "coordinates"
      type        = "GEOGRAPHY"
      mode        = "REQUIRED"
      description = "Geographical position as a Point (WKT format: POINT(longitude latitude))"
    },
    {
      name        = "services"
      type        = "STRING"
      mode        = "REPEATED"
      description = "Available services at the station (e.g., RESTAURANT, RESTROOM, SHOP)"
    },
    {
      name        = "phone"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "Contact phone number for the station"
    },
    {
      name        = "created_at"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "Record creation timestamp"
    },
    {
      name        = "updated_at"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "Record last update timestamp"
    }
  ])

  # Prevent accidental schema changes
  lifecycle {
    ignore_changes = [schema]
  }

  depends_on = [
    google_bigquery_dataset.soste_app_dev,
    google_project_service.required_apis
  ]
}

# ==========================================
# BIGQUERY DATASET ACCESS CONTROLS
# ==========================================
# Grant the service account explicit dataset-level permissions

resource "google_bigquery_dataset_iam_member" "adk_agent_editor" {
  dataset_id = google_bigquery_dataset.soste_app_dev.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.adk_agent.email}"
  project    = var.gcp_project
}

# ==========================================
# BIGQUERY TABLE ACCESS CONTROLS
# ==========================================
# Grant explicit table-level permissions

resource "google_bigquery_table_iam_member" "adk_agent_editor" {
  dataset_id = google_bigquery_dataset.soste_app_dev.dataset_id
  table_id   = google_bigquery_table.db_soste.table_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.adk_agent.email}"
  project    = var.gcp_project
}
