# ==========================================
# CLOUD RUN 3-SERVICE DISTRIBUTED STACK (v2)
# ==========================================
# Deploys the 3 SostaApp microservices from a shared container image:
# 1. MCP SSE Server (`adk-agent-dev-mcp-sse`)         -> SERVICE_ROLE=mcp
# 2. Suggeritore A2A Server (`adk-agent-dev-suggeritore-a2a`) -> SERVICE_ROLE=a2a
# 3. SostaApp Production Runner (`adk-agent-dev`)     -> SERVICE_ROLE=runner

locals {
  cloud_run_v2_ingress_map = {
    "all"                               = "INGRESS_TRAFFIC_ALL"
    "internal"                          = "INGRESS_TRAFFIC_INTERNAL_ONLY"
    "internal-and-cloud-load-balancing" = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  }
  # Allow external HTTPS invocation for the distributed stack while enforcing IAM/OIDC auth
  effective_v2_ingress = lookup(local.cloud_run_v2_ingress_map, var.cloud_run_ingress, "INGRESS_TRAFFIC_ALL")

  # Service accounts granted roles/run.invoker on all 3 services
  invoker_members = distinct(compact([
    "serviceAccount:${google_service_account.adk_agent.email}",
    "serviceAccount:terraform-admin@${var.gcp_project}.iam.gserviceaccount.com",
    var.impersonate_service_account != "" ? "serviceAccount:${var.impersonate_service_account}" : "",
  ]))
}

# ------------------------------------------------------------------------------
# 1. MCP SSE SERVER (BigQuery Geospatial Tool Server)
# ------------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "mcp_sse" {
  name     = local.cloud_run_config.mcp_service_name
  location = var.gcp_region
  project  = var.gcp_project
  ingress  = local.effective_v2_ingress

  template {
    service_account = google_service_account.adk_agent.email
    timeout         = "${local.cloud_run_config.timeout}s"

    scaling {
      min_instance_count = local.cloud_run_config.min_instances
      max_instance_count = local.cloud_run_config.max_instances
    }

    containers {
      image = var.cloud_run_image_url

      resources {
        limits = {
          cpu    = local.cloud_run_config.cpu
          memory = local.cloud_run_config.memory
        }
        cpu_idle = true
      }

      env {
        name  = "SERVICE_ROLE"
        value = "mcp"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "1"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.gcp_project
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.gcp_region
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "BIGQUERY_DATASET"
        value = local.bigquery_config.dataset_id
      }
      env {
        name  = "BIGQUERY_TABLE"
        value = local.bigquery_config.table_id
      }

      ports {
        container_port = 8080
      }

      startup_probe {
        http_get {
          path = "/health/ready"
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 12
      }

      liveness_probe {
        http_get {
          path = "/health/live"
          port = 8080
        }
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 15
        failure_threshold     = 3
      }
    }
  }

  labels = local.common_labels

  depends_on = [
    google_project_service.required_apis,
    google_service_account.adk_agent,
    google_bigquery_table.db_soste,
  ]
}

# ------------------------------------------------------------------------------
# 2. SUGGERITORE A2A SERVER (Remote Trip Optimization Microservice)
# ------------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "suggeritore_a2a" {
  name     = local.cloud_run_config.suggeritore_service_name
  location = var.gcp_region
  project  = var.gcp_project
  ingress  = local.effective_v2_ingress

  template {
    service_account = google_service_account.adk_agent.email
    timeout         = "${local.cloud_run_config.timeout}s"

    scaling {
      min_instance_count = local.cloud_run_config.min_instances
      max_instance_count = local.cloud_run_config.max_instances
    }

    containers {
      image = var.cloud_run_image_url

      resources {
        limits = {
          cpu    = local.cloud_run_config.cpu
          memory = local.cloud_run_config.memory
        }
        cpu_idle = true
      }

      env {
        name  = "SERVICE_ROLE"
        value = "a2a"
      }
      env {
        name  = "MCP_SSE_URL"
        value = "${google_cloud_run_v2_service.mcp_sse.uri}/sse"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "1"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.gcp_project
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.gcp_region
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "FIRESTORE_FOOD_KB_DB"
        value = google_firestore_database.food_knowledge_base.name
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.product_specs_bucket.name
      }
      env {
        name  = "VERTEX_RAG_LOCATION"
        value = "europe-west3"
      }
      env {
        name  = "VERTEX_RAG_CORPUS_DISPLAY_NAME"
        value = "sosta-product-specs-corpus"
      }

      ports {
        container_port = 8080
      }

      startup_probe {
        http_get {
          path = "/health/ready"
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 12
      }

      liveness_probe {
        http_get {
          path = "/health/live"
          port = 8080
        }
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 15
        failure_threshold     = 3
      }
    }
  }

  labels = local.common_labels

  depends_on = [
    google_cloud_run_v2_service.mcp_sse,
    google_firestore_database.food_knowledge_base,
    google_storage_bucket.product_specs_bucket,
  ]
}

# ------------------------------------------------------------------------------
# 3. SOSTA APP PRODUCTION RUNNER (FastAPI + Firestore Session & Memory Services)
# ------------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "adk_agent" {
  name     = local.cloud_run_config.service_name
  location = var.gcp_region
  project  = var.gcp_project
  ingress  = local.effective_v2_ingress

  template {
    service_account = google_service_account.adk_agent.email
    timeout         = "${local.cloud_run_config.timeout}s"

    scaling {
      min_instance_count = local.cloud_run_config.min_instances
      max_instance_count = local.cloud_run_config.max_instances
    }

    containers {
      image = var.cloud_run_image_url

      resources {
        limits = {
          cpu    = local.cloud_run_config.cpu
          memory = local.cloud_run_config.memory
        }
        cpu_idle = true
      }

      env {
        name  = "SERVICE_ROLE"
        value = "runner"
      }
      env {
        name  = "SUGGERITORE_A2A_URL"
        value = google_cloud_run_v2_service.suggeritore_a2a.uri
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "1"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.gcp_project
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.gcp_region
      }
      env {
        name  = "FIRESTORE_APP_DB"
        value = google_firestore_database.application_db.name
      }
      env {
        name  = "FIRESTORE_SESSION_DB"
        value = google_firestore_database.adk_session_memory.name
      }
      env {
        name  = "FIRESTORE_FOOD_KB_DB"
        value = google_firestore_database.food_knowledge_base.name
      }
      env {
        name  = "BIGQUERY_DATASET"
        value = local.bigquery_config.dataset_id
      }
      env {
        name  = "BIGQUERY_TABLE"
        value = local.bigquery_config.table_id
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.product_specs_bucket.name
      }

      dynamic "env" {
        for_each = var.cloud_run_environment_variables
        content {
          name  = env.key
          value = env.value
        }
      }

      ports {
        container_port = 8080
      }

      startup_probe {
        http_get {
          path = "/health/ready"
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 5
        period_seconds        = 5
        failure_threshold     = 15
      }

      liveness_probe {
        http_get {
          path = "/health/live"
          port = 8080
        }
        initial_delay_seconds = 15
        timeout_seconds       = 5
        period_seconds        = 15
        failure_threshold     = 3
      }
    }
  }

  labels = local.common_labels

  depends_on = [
    google_cloud_run_v2_service.suggeritore_a2a,
    google_firestore_database.application_db,
    google_firestore_database.adk_session_memory,
    google_firestore_database.food_knowledge_base,
  ]
}

# ==========================================
# CLOUD RUN IAM INVOKER POLICIES
# ==========================================
# 1. Authenticated Service-to-Service & Admin Invokers (OIDC Identity Tokens)
resource "google_cloud_run_v2_service_iam_member" "mcp_sse_invokers" {
  for_each = toset(local.invoker_members)

  project  = var.gcp_project
  location = var.gcp_region
  name     = google_cloud_run_v2_service.mcp_sse.name
  role     = "roles/run.invoker"
  member   = each.value
}

resource "google_cloud_run_v2_service_iam_member" "suggeritore_a2a_invokers" {
  for_each = toset(local.invoker_members)

  project  = var.gcp_project
  location = var.gcp_region
  name     = google_cloud_run_v2_service.suggeritore_a2a.name
  role     = "roles/run.invoker"
  member   = each.value
}

resource "google_cloud_run_v2_service_iam_member" "adk_agent_invokers" {
  for_each = toset(local.invoker_members)

  project  = var.gcp_project
  location = var.gcp_region
  name     = google_cloud_run_v2_service.adk_agent.name
  role     = "roles/run.invoker"
  member   = each.value
}

# 2. Optional Public Unauthenticated Access (if enabled via cloud_run_allow_public_access)
resource "google_cloud_run_v2_service_iam_member" "public_access_runner" {
  count    = var.cloud_run_allow_public_access ? 1 : 0
  project  = var.gcp_project
  location = var.gcp_region
  name     = google_cloud_run_v2_service.adk_agent.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
