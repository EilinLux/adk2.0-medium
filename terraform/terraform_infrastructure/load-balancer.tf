# ==============================================================================
# EXTERNAL APPLICATION LOAD BALANCER & SERVERLESS NEG FOR CLOUD RUN
# ==============================================================================
# Provides a hardened public entrypoint for the multi-agent SostaApp runner:
# 1. Global external IPv4 address (`google_compute_global_address`)
# 2. Regional Serverless Network Endpoint Group (`google_compute_region_network_endpoint_group`)
# 3. External Managed Backend Service with Cloud Armor WAF attachment (`google_compute_backend_service`)
# 4. URL Map routing to the SostaApp runner (`google_compute_url_map`)
# 5. Global HTTP Target Proxy & Forwarding Rule (`google_compute_global_forwarding_rule`)
#
# Architectural isolation:
# - Only the `adk_agent` (runner) service is exposed through the load balancer.
# - Internal microservices (`mcp_sse` and `suggeritore_a2a`) remain unexposed,
#   accessible only via authenticated IAM/OIDC service-to-service calls.

# ------------------------------------------------------------------------------
# 1. GLOBAL EXTERNAL IP ADDRESS
# ------------------------------------------------------------------------------
resource "google_compute_global_address" "lb_ip" {
  name        = "${local.resource_prefix}-lb-ip"
  project     = var.gcp_project
  description = "Global IPv4 address for SostaApp External Application Load Balancer"
}

# ------------------------------------------------------------------------------
# 2. REGIONAL SERVERLESS NEG (Targets SostaApp Cloud Run Runner)
# ------------------------------------------------------------------------------
resource "google_compute_region_network_endpoint_group" "runner_neg" {
  name                  = "${local.resource_prefix}-runner-neg"
  project               = var.gcp_project
  region                = var.gcp_region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.adk_agent.name
  }
}

# ------------------------------------------------------------------------------
# 3. BACKEND SERVICE WITH CLOUD ARMOR WAF ATTACHMENT
# ------------------------------------------------------------------------------
resource "google_compute_backend_service" "runner_backend" {
  name                  = "${local.resource_prefix}-runner-backend"
  project               = var.gcp_project
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTPS"
  port_name             = "http"
  timeout_sec           = var.lb_backend_timeout_sec # Default 300s to support long SSE generative streaming
  security_policy       = google_compute_security_policy.sosta_armor.id

  backend {
    group = google_compute_region_network_endpoint_group.runner_neg.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# ------------------------------------------------------------------------------
# 4. URL MAP
# ------------------------------------------------------------------------------
resource "google_compute_url_map" "lb_url_map" {
  name            = "${local.resource_prefix}-lb-url-map"
  project         = var.gcp_project
  default_service = google_compute_backend_service.runner_backend.id
}

# ------------------------------------------------------------------------------
# 5. TARGET HTTP PROXY & GLOBAL FORWARDING RULE (PORT 80)
# ------------------------------------------------------------------------------
resource "google_compute_target_http_proxy" "http_proxy" {
  name    = "${local.resource_prefix}-lb-http-proxy"
  project = var.gcp_project
  url_map = google_compute_url_map.lb_url_map.id
}

resource "google_compute_global_forwarding_rule" "http_forwarding_rule" {
  name                  = "${local.resource_prefix}-lb-forwarding-rule"
  project               = var.gcp_project
  target                = google_compute_target_http_proxy.http_proxy.id
  port_range            = "80"
  ip_address            = google_compute_global_address.lb_ip.address
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

# ------------------------------------------------------------------------------
# OPTIONAL MANAGED SSL / HTTPS TERMINATION
# ------------------------------------------------------------------------------
# For custom domain production deployment with Google-managed SSL certificates:
#
# resource "google_compute_managed_ssl_certificate" "lb_ssl" {
#   count   = length(var.lb_ssl_domains) > 0 ? 1 : 0
#   name    = "${local.resource_prefix}-managed-cert"
#   project = var.gcp_project
#
#   managed {
#     domains = var.lb_ssl_domains
#   }
# }
#
# resource "google_compute_target_https_proxy" "https_proxy" {
#   count            = length(var.lb_ssl_domains) > 0 ? 1 : 0
#   name             = "${local.resource_prefix}-lb-https-proxy"
#   project          = var.gcp_project
#   url_map          = google_compute_url_map.lb_url_map.id
#   ssl_certificates = [google_compute_managed_ssl_certificate.lb_ssl[0].id]
# }
#
# resource "google_compute_global_forwarding_rule" "https_forwarding_rule" {
#   count                 = length(var.lb_ssl_domains) > 0 ? 1 : 0
#   name                  = "${local.resource_prefix}-lb-https-forwarding-rule"
#   project               = var.gcp_project
#   target                = google_compute_target_https_proxy.https_proxy[0].id
#   port_range            = "443"
#   ip_address            = google_compute_global_address.lb_ip.address
#   load_balancing_scheme = "EXTERNAL_MANAGED"
# }
