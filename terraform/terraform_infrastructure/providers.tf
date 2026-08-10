provider "google" {
  project                     = var.gcp_project
  region                      = var.gcp_region
  impersonate_service_account = var.impersonate_service_account != "" ? var.impersonate_service_account : null
}

provider "google-beta" {
  project                     = var.gcp_project
  region                      = var.gcp_region
  impersonate_service_account = var.impersonate_service_account != "" ? var.impersonate_service_account : null
}