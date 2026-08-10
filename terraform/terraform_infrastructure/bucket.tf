# ------------------------------------------------------------------------------
# Cloud Storage Bucket Resource
# ------------------------------------------------------------------------------
resource "google_storage_bucket" "product_specs_bucket" {
  name                     = local.product_specs_bucket_config.name
  location                 = local.product_specs_bucket_config.region
  project                  = var.gcp_project
  force_destroy            = false
  storage_class            = "STANDARD"
  public_access_prevention = "enforced"

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "product-knowledge-base"
  }
}