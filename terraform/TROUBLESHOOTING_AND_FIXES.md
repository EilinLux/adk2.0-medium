# Terraform & GCP Setup — Troubleshooting Guide & Resolved Errors

This document provides a comprehensive summary of all errors encountered during the Google Cloud and Terraform setup for the **ADK 2.0 Multi-Agent System**, explaining the root causes, the solutions applied, and the specific code modifications made across the repository.

---

## Table of Contents
1. [Overview of Active Environment](#overview-of-active-environment)
2. [Error 1: Stale Quota Project & `USER_PROJECT_DENIED`](#error-1-stale-quota-project--user_project_denied)
3. [Error 2: Browser OAuth Reverting to Previous Lab Account](#error-2-browser-oauth-reverting-to-previous-lab-account)
4. [Error 3: `gcloud projects create` Failed](#error-3-gcloud-projects-create-failed)
5. [Error 4: `Policy update access denied` / `setIamPolicy` Restrictions](#error-4-policy-update-access-denied--setiampolicy-restrictions)
6. [Error 5: Silent Freeze in `setup.sh` at "Setting Up Artifact Registry"](#error-5-silent-freeze-in-setupsh-at-setting-up-artifact-registry)
7. [Error 6: GCS Bucket 409 Conflict (`The requested bucket name is not available`)](#error-6-gcs-bucket-409-conflict-the-requested-bucket-name-is-not-available)
8. [Error 7: `403 AccessDenied` on Remote State Bucket after Account Switch](#error-7-403-accessdenied-on-remote-state-bucket-after-account-switch)
9. [Summary of Modified Files & Diffs](#summary-of-modified-files--diffs)
10. [Final Verification & Deployment Instructions](#final-verification--deployment-instructions)

---

## 1. Overview of Active Environment

* **Active GCP User**: `devstar7501@gcplab.me`
* **Active GCP Project ID**: `gai-community29oct-7501`
* **Default Region**: `europe-west1`
* **Remote State Bucket**: `gs://terraform-state-gai-community29oct-7501`
* **Artifact Registry Repository**: `europe-west1-docker.pkg.dev/gai-community29oct-7501/adk-agent`
* **Product Specs GCS Bucket**: `gs://adk-agent-dev-gai-community29oct-7501-product-specs`

---

## 2. Error 1: Stale Quota Project & `USER_PROJECT_DENIED`

### Symptoms
When running `gcloud auth application-default login` or `gcloud auth application-default set-quota-project`:
```text
ERROR: (gcloud.auth.application-default.set-quota-project) [devstar7500@gcplab.me] does not have permission to access projects instance [gai-community29oct-7500:testIamPermissions]
reason: USER_PROJECT_DENIED
Caller does not have required permission to use project gai-community29oct-7500. Grant the caller the roles/serviceusage.serviceUsageConsumer role...
```

### Root Cause
An obsolete project ID (`gai-community29oct-7500`) was saved in the gcloud configuration under `[billing] quota_project`. When gcloud or client libraries made API requests, Google Cloud checked permissions against the quota project first. Since the active identity had no rights on that old project, every request was immediately rejected.

### Solution Applied
Unset the persistent quota project property:
```bash
gcloud config unset billing/quota_project
```

---

## 3. Error 2: Browser OAuth Reverting to Previous Lab Account

### Symptoms
Running `gcloud auth login` or `gcloud auth application-default login` repeatedly authenticated as `devstar7500@gcplab.me` instead of the newly assigned student identity.

### Root Cause
Default web browsers preserve Google session cookies. When gcloud opened the OAuth redirect link (`accounts.google.com`), Google automatically selected the active Google session (`devstar7500`) without prompting to choose or switch accounts.

### Solution Applied
Used the `--no-launch-browser` flag (or opened the URL in an Incognito/Private window where only the new lab identity was logged in):
```bash
gcloud auth login devstar7501@gcplab.me --no-launch-browser
gcloud auth application-default login --no-launch-browser
```

---

## 4. Error 3: `gcloud projects create` Failed

### Symptoms
```text
ERROR: (gcloud.projects.create) Project creation failed. The project ID you specified is already in use by another project. Please try an alternative ID.
```

### Root Cause
1. In Google Cloud, project IDs are globally unique across all GCP accounts worldwide.
2. In pre-provisioned GCP sandbox/lab environments (`@gcplab.me`), projects are created in advance by lab administrators. Lab student accounts do not have the `resourcemanager.projects.create` permission.

### Solution Applied
Skipped project creation and set the existing project directly:
```bash
gcloud config set project gai-community29oct-7501
```

---

## 5. Error 4: `Policy update access denied` / `setIamPolicy` Restrictions

### Symptoms
Running Step 3 in the README:
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:terraform-admin@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/editor"
```
Failed with:
```text
ERROR: (gcloud.projects.add-iam-policy-binding) [devstar7502@gcplab.me] does not have permission to access projects instance [gai-community29oct-7502:setIamPolicy] (or it may not exist): Policy update access denied.
```
Similarly, trying to bind token creator roles on service accounts returned:
`PERMISSION_DENIED: Permission 'iam.serviceAccounts.setIamPolicy' denied on resource`.

### Root Cause
* Granting project-level IAM roles requires `resourcemanager.projects.setIamPolicy` (`roles/resourcemanager.projectIamAdmin` or `roles/owner`).
* In the lab project, only the instructor (`romin@google.com`) holds the project IAM admin role.
* Lab student accounts (`devstarXXXX@gcplab.me`) are granted `roles/editor` plus individual service admin roles (`bigquery.admin`, `storage.admin`, `datastore.owner`, `aiplatform.admin`, `run.admin`), but are strictly barred from updating IAM policies (`setIamPolicy`).
* Therefore, creating a dedicated `terraform-admin` service account and impersonating it is impossible (and unnecessary) in this environment.

### Solutions & Code Changes
1. **Skipped Step 3 (Service account creation & impersonation)**: Since the student account already possesses direct admin access to all required services, Terraform can run directly via Application Default Credentials (ADC).
2. **Updated [`variables.tf`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure/variables.tf)**:
   Changed `impersonate_service_account` default from `"terraform-admin@..."` to `""`.
3. **Updated [`iam.tf`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure/iam.tf)**:
   Commented out all `google_project_iam_member` resources (Cloud Run, BigQuery, Firestore, Logging, Monitoring, Trace, Artifact Registry) because Terraform would fail on `setIamPolicy`. Kept the `google_service_account.adk_agent` resource intact for outputs.

---

## 6. Error 5: Silent Freeze in `setup.sh` at "Setting Up Artifact Registry"

### Symptoms
Running `./setup.sh` froze indefinitely at:
```text
=====================================
Setting Up Artifact Registry
=====================================
```

### Root Cause
Inside `setup.sh`:
```bash
if gcloud artifacts repositories describe adk-agent --location=$REGION &>/dev/null; then
```
`artifactregistry.googleapis.com` was not enabled on the project. `gcloud` stopped and prompted on stdin:
`API [artifactregistry.googleapis.com] not enabled on project. Would you like to enable and retry (this will take a few minutes)? (y/N)?`
Because stdout and stderr were redirected to `/dev/null` (`&>/dev/null`), the interactive prompt was completely invisible to the user, and the script hung waiting for input.

### Solution Applied
Pre-enabled all required APIs and created the Artifact Registry repository directly:
```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  bigquery.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudtrace.googleapis.com \
  compute.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  --project=gai-community29oct-7501

gcloud artifacts repositories create adk-agent \
  --repository-format=docker \
  --location=europe-west1 \
  --description="ADK Agent Docker images" \
  --project=gai-community29oct-7501

gcloud auth configure-docker europe-west1-docker.pkg.dev --quiet
```

---

## 7. Error 6: GCS Bucket 409 Conflict (`The requested bucket name is not available`)

### Symptoms
During `terraform apply`:
```text
Error: googleapi: Error 409: The requested bucket name is not available. The bucket namespace is shared by all users of the system. Please select a different name and try again., conflict
with google_storage_bucket.product_specs_bucket,
on bucket.tf line 4, in resource "google_storage_bucket" "product_specs_bucket":
```

### Root Cause
Google Cloud Storage bucket names exist in a **single global namespace** shared across all Google Cloud users worldwide.
In [`locals.tf`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure/locals.tf), the bucket name was statically defined as:
```hcl
name = "${local.resource_prefix}-product-specs"  # -> "adk-agent-dev-product-specs"
```
This generic name was already claimed by another user/project globally.

### Solution & Code Changes
1. **[`locals.tf`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure/locals.tf)**:
   Updated the naming pattern to include the GCP Project ID:
   ```hcl
   product_specs_bucket_config = {
     name   = "${local.resource_prefix}-${var.gcp_project}-product-specs"
     region = var.bucket_region
   }
   ```
   This resolves to `adk-agent-dev-gai-community29oct-7501-product-specs`, guaranteeing global uniqueness.
2. **[`.env`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/.env)**:
   Updated `GCS_BUCKET=adk-agent-dev-gai-community29oct-7501-product-specs`.
3. **[`upload_pdfs.py`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure/seeding/upload_pdfs.py)**:
   Updated the default fallback bucket name to `f"adk-agent-{ENVIRONMENT}-{PROJECT_ID}-product-specs"`.

---

## 8. Error 7: `403 AccessDenied` on Remote State Bucket after Account Switch

### Symptoms
```text
Error: Failed to open state file at gs://terraform-state-gai-community29oct-7502/adk-agent/dev/default.tfstate: googleapi: got HTTP response code 403 with body: Access denied. devstar7501@gcplab.me does not have storage.objects.get access...
```

### Root Cause
The active GCP session was updated from `devstar7502` to `devstar7501` (`gai-community29oct-7501`). However, [`terraform.tf`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure/terraform.tf) was still configured to use the state bucket from project `7502`, which the new user has no permission to access.

### Solution & Code Changes
1. Created the remote state bucket for project `7501`:
   ```bash
   gsutil mb -l europe-west1 -p gai-community29oct-7501 gs://terraform-state-gai-community29oct-7501
   ```
2. **[`environments/dev.tfvars`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/environments/dev.tfvars)**:
   Updated `gcp_project = "gai-community29oct-7501"`.

---

## 9. Dynamic Backend Configuration via Partial Configuration

### Why variables cannot be used in `backend "gcs"`
Terraform strictly forbids `var.*`, `local.*`, functions, or environment variables inside `terraform { backend "..." {} }`. Terraform initializes the backend *before* reading variables.

### The Solution: Partial Backend Configuration
1. **[`terraform.tf`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure/terraform.tf)**:
   The backend block is kept empty:
   ```hcl
   terraform {
     backend "gcs" {}
   }
   ```
2. **[`Makefile`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/Makefile)** & **[`setup.sh`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/setup.sh)**:
   The backend bucket and prefix are supplied dynamically via `-backend-config`:
   ```makefile
   PROJECT_ID ?= $(shell gcloud config get-value project 2>/dev/null)
   STATE_BUCKET ?= terraform-state-$(PROJECT_ID)

   init:
       cd $(TF_DIR) && terraform init -upgrade -reconfigure \
           -backend-config="bucket=$(STATE_BUCKET)" \
           -backend-config="prefix=adk-agent/$(ENV)"
   ```
   Now, whenever you switch accounts or projects, `make init ENV=dev` automatically binds to the right bucket without editing `.tf` files!

---

## 10. Summary of Modified Files & Diffs

| File | Changes Made |
| :--- | :--- |
| **`terraform_infrastructure/terraform.tf`** | Converted `backend "gcs"` to an empty partial configuration block. |
| **`Makefile`** | Added dynamic `PROJECT_ID` / `STATE_BUCKET` detection and updated `init` with `-backend-config`. |
| **`setup.sh`** | Updated `initialize_terraform` to dynamically inject `-backend-config` with the active project. |
| **`terraform_infrastructure/variables.tf`** | Changed `impersonate_service_account` default from `"terraform-admin@..."` to `""`. |
| **`terraform_infrastructure/iam.tf`** | Commented out all `google_project_iam_member` resources to avoid `setIamPolicy` failures. |
| **`terraform_infrastructure/locals.tf`** | Changed bucket name from `"${local.resource_prefix}-product-specs"` to `"${local.resource_prefix}-${var.gcp_project}-product-specs"`. |
| **`environments/dev.tfvars`** | Updated `gcp_project` to `"gai-community29oct-7501"`. |
| **`.env`** | Updated `GOOGLE_CLOUD_PROJECT=gai-community29oct-7501` and `GCS_BUCKET=adk-agent-dev-gai-community29oct-7501-product-specs`. |
| **`terraform_infrastructure/seeding/upload_pdfs.py`** | Updated fallback bucket formula to incorporate `{PROJECT_ID}`. |

---

## 10. Final Verification & Deployment Instructions

The configuration has been tested and validated with `terraform plan`:
* **Plan Output**: **27 resources to add**, 0 to change, 0 to destroy.
* **Resources Included**:
  * BigQuery Dataset (`soste_app_dev`) and Table (`db_soste`)
  * 3 Firestore Databases (`adk-agent-dev-session-memory-fs`, `adk-agent-dev-food-kb-fs`, `adk-agent-dev-application-db-fs`)
  * GCS Product Specs Bucket (`adk-agent-dev-gai-community29oct-7501-product-specs`)
  * Service Account (`adk-agent-dev-sa`)
  * Required API Services

### To apply the deployment:
```bash
cd /Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure
terraform apply -var-file=../environments/dev.tfvars
```
When prompted:
```text
Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes
```

### To run the database seeding scripts afterward:
```bash
cd /Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure
uv run python seeding/firestore_app_db_seed.py
uv run python seeding/firestore_food_kb_seed.py
uv run python seeding/firestore_memory_seed.py
uv run python seeding/bq_seed.py
uv run python seeding/upload_pdfs.py
```
