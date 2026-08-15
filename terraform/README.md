# Terraform Infrastructure Guide

This directory manages the provisioning of all Google Cloud Platform (GCP) resources required by the **ADK Multi-Agent System** using Terraform.

---

## Architecture Overview

Terraform automates the deployment of the following resources:

* **BigQuery**:
  * Dataset: `soste_app_dev` (EU/europe-west1)
  * Table: `db_soste` (Service station locations, fuel types, coordinates)
  * Access controls for the application service account
* **Cloud Firestore**:
  * `adk-agent-dev-session-memory-fs`: Session history & memory
  * `adk-agent-dev-food-kb-fs`: Autogrill menu & food knowledge base
  * `adk-agent-dev-application-db-fs`: Application configuration & user state
  * Composite indexes for queries
* **Cloud Storage**:
  * `gs://adk-agent-dev-${PROJECT_ID}-product-specs`: Stores official Autogrill product specification PDFs for RAG grounding
* **IAM & Service Accounts**:
  * `adk-agent-dev-sa`: Application identity for Cloud Run / agent execution
* **GCP Services (APIs)**:
  * Artifact Registry, Cloud Run, Cloud Build, BigQuery, Firestore, Vertex AI, Logging, Monitoring, Cloud Trace

---

## Prerequisites

1. **Terraform** >= 1.5.0 (`terraform version`)
2. **Google Cloud SDK** (`gcloud version`)
3. **Python package runner** (`uv` or `pip`)
4. An active GCP account with billing enabled

---

## Step-by-Step Setup & Deployment

### Step 1: Authenticate with Google Cloud

Authenticate both the `gcloud` CLI and **Application Default Credentials (ADC)** used by Terraform and the Python SDK:

```bash
# 1. Set your active project
gcloud config set project YOUR_PROJECT_ID

# 2. Authenticate CLI
gcloud auth login

# 3. Authenticate Application Default Credentials (ADC)
gcloud auth application-default login

# 4. Set quota project to prevent billing/quota errors
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

> [!TIP]
> If you are working in an Incognito / remote session or machine without a popup browser, append `--no-launch-browser` to the login commands.

---

### Step 2: Create Remote State Bucket & Enable APIs

Create the GCS bucket used by Terraform to store remote state (matches the naming convention `terraform-state-${PROJECT_ID}`):

```bash
export PROJECT_ID=$(gcloud config get-value project)

# Create state bucket in europe-west1
gsutil mb -l europe-west1 -p $PROJECT_ID gs://terraform-state-${PROJECT_ID}
```

Pre-enable the foundational APIs:

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
  --project=$PROJECT_ID
```

---

### Step 3: Configure Environment Variables

Edit [`environments/dev.tfvars`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/environments/dev.tfvars):

```hcl
gcp_project = "YOUR_PROJECT_ID"
gcp_region  = "europe-west1"
environment = "dev"
```

Also update your local [`.env`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/.env) file in the root of `adk2.0-medium`:

```bash
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GCS_BUCKET=adk-agent-dev-YOUR_PROJECT_ID-product-specs
```

---

### Step 4: Initialize Terraform (Dynamic Partial Backend)

This configuration uses Terraform's **Partial Configuration** pattern. The backend state bucket is dynamically bound from your active `gcloud` project, eliminating hardcoded project IDs in `.tf` files.

#### Option A: Using the Makefile (Recommended)
```bash
make init ENV=dev
```

#### Option B: Using Terraform CLI directly
```bash
cd terraform_infrastructure

terraform init -reconfigure \
  -backend-config="bucket=terraform-state-${PROJECT_ID}" \
  -backend-config="prefix=adk-agent/dev"
```

---

### Step 5: Plan and Deploy

#### Option A: Using the Makefile
```bash
# Preview changes
make plan ENV=dev

# Apply changes
make apply ENV=dev
```

#### Option B: Using Terraform CLI directly
```bash
cd terraform_infrastructure

# Plan
terraform plan -var-file=../environments/dev.tfvars

# Apply
terraform apply -var-file=../environments/dev.tfvars
```

---

### Step 6: Populate Database & Data Sources (Seeding)

Once Terraform provisions the infrastructure, seed the initial data into BigQuery, Firestore, and Cloud Storage:

```bash
cd terraform_infrastructure

uv run python seeding/firestore_app_db_seed.py
uv run python seeding/firestore_food_kb_seed.py
uv run python seeding/firestore_memory_seed.py
uv run python seeding/bq_seed.py
uv run python seeding/upload_pdfs.py
```

---

## Makefile Reference

The root [`Makefile`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/Makefile) provides convenient shorthands for all common operations:

| Command | Description |
| :--- | :--- |
| `make init ENV=dev` | Initializes Terraform with dynamic backend bucket from active `gcloud` project. |
| `make plan ENV=dev` | Generates execution plan against `environments/dev.tfvars`. |
| `make apply ENV=dev` | Deploys all planned infrastructure changes. |
| `make destroy ENV=dev` | Destroys provisioned infrastructure resources. |
| `make validate` | Validates Terraform syntax and configuration. |
| `make fmt` | Formats all `.tf` files recursively. |
| `make clean` | Cleans `.terraform/` cache and plan files. |

---

## Important Architectural Notes

1. **No Hardcoded State Buckets**:
   In [`terraform_infrastructure/terraform.tf`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure/terraform.tf), `backend "gcs" {}` is defined empty. The bucket is supplied dynamically at `init` time via `-backend-config` so teams can easily switch projects without editing code.
2. **Globally Unique Storage Buckets**:
   In [`terraform_infrastructure/locals.tf`](file:///Users/zelda.luconi/Medium/adk2.0-blackboard/adk2.0-medium/terraform/terraform_infrastructure/locals.tf), GCS bucket names incorporate `${var.gcp_project}` (`adk-agent-dev-${var.gcp_project}-product-specs`) to prevent global namespace collisions (409 Conflict).
3. **Sandboxed & Workshop Environments**:
   In restricted lab environments (e.g. `@gcplab.me`), user accounts lack `resourcemanager.projects.setIamPolicy` permissions. Dedicated service account impersonation is disabled (`impersonate_service_account = ""`) and project-level IAM bindings in `iam.tf` are commented out, allowing the deployment to run smoothly using your authenticated user identity.