terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.25"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.25"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Uncomment this block once you've created a GCS bucket for remote state
  # backend "gcs" {
  #   bucket = "terraform-state-${var.gcp_project}"
  #   prefix = "adk-agent/${var.environment}"
  # }
}
