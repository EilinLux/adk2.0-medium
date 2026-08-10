# ==========================================
# ENABLE REQUIRED GCP APIS
# ==========================================
# Enable all required Google Cloud APIs for the ADK agent application

resource "google_project_service" "required_apis" {
  for_each = toset(local.gcp_services)

  project = var.gcp_project
  service = each.key

  # IMPORTANT: Set to false to prevent accidental disabling of APIs
  # when running 'terraform destroy'. This prevents breaking other
  # services that depend on these APIs.
  disable_on_destroy = false

  timeouts {
    create = "10m"
    update = "10m"
  }
}

# All APIs are managed through google_project_service resources above
