# ==========================================
# PROJECT AND ENVIRONMENT VARIABLES
# ==========================================

variable "gcp_project" {
  description = "Google Cloud Project ID"
  type        = string
  validation {
    condition     = can(regex("^[a-z][-a-z0-9]*[a-z0-9]$", var.gcp_project))
    error_message = "GCP project must be a valid project ID format."
  }
}



variable "impersonate_service_account" {
  type        = string
  description = "Service Account email to impersonate during execution"
  default     = "terraform-admin@adk-workshop-sosta-app-dev.iam.gserviceaccount.com"
}

variable "gcp_region" {
  description = "Google Cloud region for resources"
  type        = string
  default     = "europe-west1"
  validation {
    condition     = can(regex("^[a-z]+-[a-z0-9]+$", var.gcp_region))
    error_message = "Invalid GCP region format."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "app_display_name" {
  description = "Display name for the application"
  type        = string
  default     = "ADK Multi-Agent System"
}

# ==========================================
# BIGQUERY VARIABLES
# ==========================================

variable "bigquery_dataset_id" {
  description = "BigQuery dataset ID for storing application data"
  type        = string
  default     = "soste_app_dev"
}

variable "bigquery_location" {
  description = "BigQuery dataset location (e.g., EU, US, asia-southeast1)"
  type        = string
  default     = "EU"
  validation {
    condition     = contains(["EU", "US", "asia-northeast1", "asia-southeast1", "europe-west1", "europe-west4"], var.bigquery_location)
    error_message = "Unsupported BigQuery location."
  }
}

variable "bigquery_table_id" {
  description = "BigQuery table ID for service station data"
  type        = string
  default     = "db_soste"
}

variable "bigquery_table_expiration_days" {
  description = "Number of days before BigQuery table expires (0 = never)"
  type        = number
  default     = 0
}

# ==========================================
# FIRESTORE VARIABLES
# ==========================================

variable "firestore_location" {
  description = "Firestore database location (e.g., europe-west1, us-central1)"
  type        = string
  default     = "europe-west1"
}

variable "firestore_delete_protection" {
  description = "Enable delete protection for Firestore databases in production"
  type        = bool
  default     = true
}

# ==========================================
# CLOUD STORAGE VARIABLES
# ==========================================

variable "bucket_region" {
  description = "The GCP region where the Cloud Storage bucket is deployed."
  type        = string
  default     = "europe-west1" # Replace with your preferred region
}


# ==========================================
# CLOUD RUN VARIABLES
# ==========================================

variable "cloud_run_memory" {
  description = "Memory allocation for Cloud Run service (e.g., 512Mi, 1Gi, 2Gi)"
  type        = string
  default     = "2Gi"
  validation {
    condition     = can(regex("^\\d+(Mi|Gi)$", var.cloud_run_memory))
    error_message = "Memory must be in format like 512Mi, 1Gi, 2Gi."
  }
}

variable "cloud_run_cpu" {
  description = "CPU allocation for Cloud Run service (e.g., 1, 2, 4)"
  type        = string
  default     = "2"
  validation {
    condition     = can(regex("^[1-4](\\.\\d+)?$", var.cloud_run_cpu))
    error_message = "CPU must be 1, 2, 4 or a decimal value."
  }
}

variable "cloud_run_timeout" {
  description = "Request timeout in seconds (max 3600)"
  type        = number
  default     = 300
  validation {
    condition     = var.cloud_run_timeout > 0 && var.cloud_run_timeout <= 3600
    error_message = "Timeout must be between 1 and 3600 seconds."
  }
}

variable "cloud_run_min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 0
  validation {
    condition     = var.cloud_run_min_instances >= 0
    error_message = "Minimum instances must be 0 or greater."
  }
}

variable "cloud_run_max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 100
  validation {
    condition     = var.cloud_run_max_instances >= 1
    error_message = "Maximum instances must be 1 or greater."
  }
}

variable "cloud_run_image_url" {
  description = "Container image URL for Cloud Run service"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9.-]+/[a-z0-9._/-]+(@sha256:[a-f0-9]{64}|:[a-z0-9._-]+)?$", var.cloud_run_image_url))
    error_message = "Invalid container image URL format."
  }
}

variable "cloud_run_environment_variables" {
  description = "Environment variables to set in Cloud Run service"
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "cloud_run_allow_public_access" {
  description = "Whether to allow public (unauthenticated) access to Cloud Run service"
  type        = bool
  default     = false
}

variable "cloud_run_ingress" {
  description = "Ingress settings for Cloud Run (all, internal, internal-and-cloud-load-balancing)"
  type        = string
  default     = "internal-and-cloud-load-balancing"
  validation {
    condition     = contains(["all", "internal", "internal-and-cloud-load-balancing"], var.cloud_run_ingress)
    error_message = "Ingress must be one of: all, internal, internal-and-cloud-load-balancing."
  }
}

# ==========================================
# SERVICE ACCOUNT VARIABLES
# ==========================================

variable "service_account_display_name" {
  description = "Display name for the service account"
  type        = string
  default     = "ADK Agent Service Account"
}

variable "service_account_extra_roles" {
  description = "Additional IAM roles to grant to the service account"
  type        = list(string)
  default     = []
}

# ==========================================
# AUTHENTICATION & SECURITY VARIABLES
# ==========================================

variable "require_authentication" {
  description = "Require authentication for Cloud Run service"
  type        = bool
  default     = true
}

variable "cors_allowed_origins" {
  description = "CORS allowed origins for the API"
  type        = list(string)
  default     = ["https://example.com"]
}

# ==========================================
# MONITORING AND LOGGING VARIABLES
# ==========================================

variable "enable_cloud_trace" {
  description = "Enable Cloud Trace for distributed tracing"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
  validation {
    condition     = var.log_retention_days >= 1
    error_message = "Log retention days must be at least 1."
  }
}