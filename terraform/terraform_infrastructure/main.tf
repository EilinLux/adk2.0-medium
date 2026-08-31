# ==========================================
# MAIN TERRAFORM CONFIGURATION
# ==========================================
# This file orchestrates the deployment of the ADK Agent infrastructure.
# All resources are defined in separate files organized by concern:
#
# - terraform.tf: Version and backend configuration
# - providers.tf: Provider configuration
# - locals.tf: Centralized naming and configuration
# - variables.tf: Input variables with validation
# - apis.tf: GCP API enablement
# - iam.tf: Service accounts and IAM roles
# - bigquery.tf: BigQuery datasets and tables
# - firestore.tf: Firestore databases and indexes
# - cloud-run.tf: Cloud Run service
# - outputs.tf: Output values

# Note: All resource definitions have been moved to their respective files
# for better organization and maintainability.
