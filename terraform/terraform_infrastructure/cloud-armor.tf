# ==========================================
# GOOGLE CLOUD ARMOR SECURITY POLICY (WAF)
# ==========================================
# Protects the SostaApp Cloud Run production runner through perimeter defenses:
# 1. Geographic restriction / Geo-fencing (priority 5, optional)
# 2. OWASP Top 10 Core Rule Set (CRS v4.22) rules (priorities 100-107)
# 3. Known zero-day / CVE canaries (priorities 200-201)
# 4. IP-based adaptive rate limiting (priority 1000)
# 5. Default allow rule for legitimate traffic (priority 2147483647)

resource "google_compute_security_policy" "sosta_armor" {
  project     = var.gcp_project
  name        = "${local.resource_prefix}-armor"
  description = "Cloud Armor WAF policy protecting SostaApp runner with OWASP CRS 4.22, CVE canary shields, geo-fencing, and IP rate limiting."

  # ------------------------------------------------------------------------------
  # 1. GEOGRAPHIC RESTRICTION (GEO-FENCING)
  # ------------------------------------------------------------------------------
  dynamic "rule" {
    for_each = var.cloud_armor_enforce_geo_fencing ? [1] : []
    content {
      action   = "deny(403)"
      priority = 5
      match {
        expr {
          expression = join(" && ", [for r in var.cloud_armor_allowed_regions : "origin.region_code != '${r}'"])
        }
      }
      description = "Deny requests from non-whitelisted geographical regions"
    }
  }

  # ------------------------------------------------------------------------------
  # 2. OWASP CORE RULE SET (CRS v4.22 - Sensitivity 1 for low false positives)
  # ------------------------------------------------------------------------------
  rule {
    action   = "deny(403)"
    priority = 100
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('sqli-v422-stable', {'sensitivity': 1})"
      }
    }
    description = "OWASP CRS v4.22: SQL injection protection"
  }

  rule {
    action   = "deny(403)"
    priority = 101
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('xss-v422-stable', {'sensitivity': 1})"
      }
    }
    description = "OWASP CRS v4.22: Cross-site scripting (XSS) protection"
  }

  rule {
    action   = "deny(403)"
    priority = 103
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('rfi-v422-stable', {'sensitivity': 1})"
      }
    }
    description = "OWASP CRS v4.22: Remote file inclusion (RFI) protection"
  }

  rule {
    action   = "deny(403)"
    priority = 104
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('rce-v422-stable', {'sensitivity': 1})"
      }
    }
    description = "OWASP CRS v4.22: Remote code execution (RCE) protection"
  }

  rule {
    action   = "deny(403)"
    priority = 105
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('protocolattack-v422-stable', {'sensitivity': 1})"
      }
    }
    description = "OWASP CRS v4.22: Protocol attack protection"
  }

  rule {
    action   = "deny(403)"
    priority = 106
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('scannerdetection-v422-stable', {'sensitivity': 1})"
      }
    }
    description = "OWASP CRS v4.22: Scanner and crawler detection"
  }

  rule {
    action   = "deny(403)"
    priority = 107
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('sessionfixation-v422-stable', {'sensitivity': 1})"
      }
    }
    description = "OWASP CRS v4.22: Session fixation protection"
  }

  # ------------------------------------------------------------------------------
  # 3. ZERO-DAY & CVE CANARY SHIELDS
  # ------------------------------------------------------------------------------
  rule {
    action   = "deny(403)"
    priority = 200
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('cve-canary')"
      }
    }
    description = "Known CVE protections (Log4j, Spring4Shell, React RCE)"
  }

  rule {
    action   = "deny(403)"
    priority = 201
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('json-sqli-canary')"
      }
    }
    description = "JSON-based SQL injection bypass protections"
  }

  # ------------------------------------------------------------------------------
  # 4. ADAPTIVE IP RATE LIMITING (HTTP 429)
  # ------------------------------------------------------------------------------
  rule {
    action   = "throttle"
    priority = 1000
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      rate_limit_threshold {
        count        = var.cloud_armor_rate_limit_count
        interval_sec = var.cloud_armor_rate_limit_interval_sec
      }
    }
    description = "IP rate limiting: maximum ${var.cloud_armor_rate_limit_count} requests per ${var.cloud_armor_rate_limit_interval_sec}s window"
  }

  # ------------------------------------------------------------------------------
  # 5. DEFAULT FALLTHROUGH RULE (Priority 2147483647)
  # ------------------------------------------------------------------------------
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule for legitimate traffic"
  }
}
