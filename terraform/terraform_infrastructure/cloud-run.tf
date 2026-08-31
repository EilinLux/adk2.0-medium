# ==========================================
# CLOUD RUN SERVICE
# ==========================================
# Hosts the ADK multi-agent system on Google Cloud Run

resource "google_cloud_run_service" "adk_agent" {
  name     = local.cloud_run_config.service_name
  location = var.gcp_region
  project  = var.gcp_project

  metadata {
    annotations = {
      "run.googleapis.com/ingress" = var.cloud_run_ingress
    }
  }

  template {
    spec {
      # Service account for the Cloud Run service
      service_account_name = google_service_account.adk_agent.email

      # Container configuration
      containers {
        image = var.cloud_run_image_url

        # Resource limits
        resources {
          limits = {
            cpu    = local.cloud_run_config.cpu
            memory = local.cloud_run_config.memory
          }
        }

        # Environment variables
        dynamic "env" {
          for_each = var.cloud_run_environment_variables
          content {
            name  = env.key
            value = env.value
          }
        }

        # Port configuration
        ports {
          container_port = 8080
          name           = "http1"
        }

        # Liveness probe - checks if container is alive
        liveness_probe {
          http_get {
            path = "/health/live"
            port = 8080
          }
          initial_delay_seconds = 10
          period_seconds        = 10
          timeout_seconds       = 5
          failure_threshold     = 3
        }

        # Startup probe - checks if container has started
        startup_probe {
          http_get {
            path = "/health/ready"
            port = 8080
          }
          initial_delay_seconds = 0
          period_seconds        = 10
          timeout_seconds       = 3
          failure_threshold     = 3
        }
      }

      # Autoscaling configuration
      timeout_seconds = local.cloud_run_config.timeout

      # Container concurrency
      container_concurrency = 80
    }

    metadata {
      annotations = merge(
        local.common_labels,
        {
          "autoscaling.knative.dev/minScale"  = local.cloud_run_config.min_instances
          "autoscaling.knative.dev/maxScale"  = local.cloud_run_config.max_instances
          "run.googleapis.com/cpu-throttling" = "true"
          "run.googleapis.com/vpc-connector"  = "" # Leave empty unless using VPC Connector
        }
      )
    }
  }

  # Traffic configuration
  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.required_apis,
    google_service_account.adk_agent
  ]
}

# ==========================================
# CLOUD RUN SERVICE - IAM POLICY
# ==========================================
# Control who can invoke the Cloud Run service

# Allow unauthenticated access (if enabled)
resource "google_cloud_run_service_iam_member" "public_access" {
  count    = var.cloud_run_allow_public_access ? 1 : 0
  service  = google_cloud_run_service.adk_agent.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  location = var.gcp_region
  project  = var.gcp_project
}

# Restrict to authenticated users only (default)
resource "google_cloud_run_service_iam_member" "authenticated_access" {
  count    = var.require_authentication ? 1 : 0
  service  = google_cloud_run_service.adk_agent.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.adk_agent.email}"
  location = var.gcp_region
  project  = var.gcp_project
}

# ==========================================
# CLOUD RUN V2 SERVICE (ALTERNATIVE)
# ==========================================
# Uncomment below if you prefer Cloud Run v2 (jobs) instead of v1 (services)

# resource "google_cloud_run_v2_service" "adk_agent_v2" {
#   name               = local.cloud_run_config.service_name
#   location           = var.gcp_region
#   project            = var.gcp_project
#   deletion_protection = var.environment == "prod"
#
#   template {
#     service_account = google_service_account.adk_agent.email
#
#     containers {
#       image = var.cloud_run_image_url
#
#       resources {
#         cpu    = local.cloud_run_config.cpu
#         memory = local.cloud_run_config.memory
#       }
#
#       dynamic "env" {
#         for_each = var.cloud_run_environment_variables
#         content {
#           name  = env.key
#           value = env.value
#         }
#       }
#
#       ports {
#         container_port = 8080
#       }
#
#       startup_probe {
#         http_get {
#           path = "/health/ready"
#           port = 8080
#         }
#         initial_delay_seconds = 0
#         timeout_seconds       = 3
#         period_seconds        = 10
#         failure_threshold     = 3
#       }
#
#       liveness_probe {
#         http_get {
#           path = "/health/live"
#           port = 8080
#         }
#         initial_delay_seconds = 10
#         timeout_seconds       = 5
#         period_seconds        = 10
#         failure_threshold     = 3
#       }
#     }
#
#     scaling {
#       min_instance_count = local.cloud_run_config.min_instances
#       max_instance_count = local.cloud_run_config.max_instances
#     }
#
#     timeout = "${local.cloud_run_config.timeout}s"
#   }
#
#   labels = local.common_labels
# }
#
# resource "google_cloud_run_v2_service_iam_member" "public_access_v2" {
#   count    = var.cloud_run_allow_public_access ? 1 : 0
#   location = var.gcp_region
#   service  = google_cloud_run_v2_service.adk_agent_v2.name
#   role     = "roles/run.invoker"
#   member   = "allUsers"
# }

# ==========================================
# CLOUD RUN INVOKER MAPPING
# ==========================================
# For CI/CD pipelines or other services that need to invoke this service

locals {
  invoker_service_accounts = []
  # Add service accounts that should be able to invoke this service
  # Example:
  # invoker_service_accounts = [
  #   "my-ci-service-account@my-project.iam.gserviceaccount.com"
  # ]
}

resource "google_cloud_run_service_iam_member" "ci_cd_invoker" {
  for_each = toset(local.invoker_service_accounts)

  service  = google_cloud_run_service.adk_agent.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${each.value}"
  location = var.gcp_region
  project  = var.gcp_project
}
