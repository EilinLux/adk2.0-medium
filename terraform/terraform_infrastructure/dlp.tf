# ==========================================
# SENSITIVE DATA PROTECTION (CLOUD DLP)
# ==========================================
# Provisions reusable Cloud DLP Inspect and De-identify Templates for SostaApp
# to detect and mask traveler PII before prompts reach Gemini or Firestore.

resource "google_data_loss_prevention_inspect_template" "sosta_pii_inspect" {
  parent       = "projects/${var.gcp_project}/locations/${var.gcp_region}"
  template_id  = "${replace(local.resource_prefix, "-", "_")}_pii_inspect"
  display_name = "SostaApp Traveler PII Inspect Template (${var.environment})"
  description  = "Inspects prompts and tool arguments for Credit Cards, Phone Numbers, Emails, IBANs, and Italian Fiscal Codes."

  inspect_config {
    min_likelihood = "POSSIBLE"

    info_types {
      name = "CREDIT_CARD_NUMBER"
    }
    info_types {
      name = "PHONE_NUMBER"
    }
    info_types {
      name = "EMAIL_ADDRESS"
    }
    info_types {
      name = "ITALY_FISCAL_CODE"
    }
    info_types {
      name = "IBAN_CODE"
    }

    include_quote = true
  }

  depends_on = [
    google_project_service.required_apis["dlp.googleapis.com"]
  ]
}

resource "google_data_loss_prevention_deidentify_template" "sosta_pii_deidentify" {
  parent       = "projects/${var.gcp_project}/locations/${var.gcp_region}"
  template_id  = "${replace(local.resource_prefix, "-", "_")}_pii_deidentify"
  display_name = "SostaApp Traveler PII De-identify Template (${var.environment})"
  description  = "Replaces detected PII tokens with [INFO_TYPE] placeholders (e.g., [CREDIT_CARD_NUMBER], [PHONE_NUMBER])."

  deidentify_config {
    info_type_transformations {
      transformations {
        primitive_transformation {
          replace_with_info_type_config = true
        }
      }
    }
  }

  depends_on = [
    google_project_service.required_apis["dlp.googleapis.com"]
  ]
}
