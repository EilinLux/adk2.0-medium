# Terraform Quick Start Guide

## Prerequisites

- Terraform >= 1.5.0
- Google Cloud SDK (`gcloud`)
- GCP Account with billing enabled


### GCP Account Setup

1. **Create a GCP Project**
   ```bash
   gcloud projects create adk-workshop-sosta-app-dev 
   gcloud config set project adk-workshop-sosta-app-dev
   gcloud auth application-default login
   gcloud auth application-default  set-quota-project adk-workshop-sosta-app-dev
   ```

2. **Enable Required APIs** (these will be enabled by Terraform, but you can pre-enable them)
   ```bash
   gcloud services enable compute.googleapis.com
   gcloud services enable cloudresourcemanager.googleapis.com
   gcloud services enable iam.googleapis.com
   gcloud services enable cloudkms.googleapis.com
   ```

3. **Set Up Billing**
   - Go to https://console.cloud.google.com/billing
   - Create a billing account and link it to your project
   - Set up budget alerts to monitor costs

### Required Permissions

Your user account needs these roles in the GCP project:
- `Editor` (for development/staging) or
- `Cloud Run Admin`
- `BigQuery Admin`
- `Datastore Admin`
- `Cloud IAM Security Admin`
- `Artifact Registry Administrator`

---

## Initial Setup

### Step 1: Clone and Navigate to Terraform Directory

```bash
cd /path/to/adk2.0-medium
cd terraform
```

### Step 2: Authenticate with GCP

```bash
# Login to your Google Cloud account
gcloud auth login

# Set your default project
gcloud config set project adk-workshop-sosta-app-dev

# Verify authentication
gcloud auth list
gcloud config list
```

### Step 3: Create Service Account for Terraform (Recommended)

For production deployments, create a dedicated service account for Terraform:

```bash
# Set project ID
export PROJECT_ID="adk-workshop-sosta-app-dev"
export YOUR_USER_EMAIL="zelda.luconi@datwave.ai"

# Create service account
gcloud iam service-accounts create terraform-admin \
  --display-name="Terraform Admin"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:terraform-admin@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/editor"

# Create and download key
gcloud iam service-accounts add-iam-policy-binding \
  terraform-admin@adk-workshop-sosta-app-dev.iam.gserviceaccount.com \
  --member="user:$YOUR_USER_EMAIL" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project="adk-workshop-sosta-app-dev"
```

**Security Note**: Store `terraform-key.json` securely:
```bash
# Add to .gitignore
echo "terraform-key.json" >> .gitignore

# Restrict file permissions
chmod 400 terraform-key.json

# Consider using GCP Secret Manager or HashiCorp Vault in production
```

### Step 4: Initialize Terraform

```bash
# Navigate to terraform directory
cd terraform_infrastructure

# Initialize Terraform (download providers and modules)
terraform init

# Verify initialization
ls -la .terraform/
```

You should see:
```
.terraform/
├── providers/
└── modules/
```

---




## 1. Authenticate

```bash
# Login to Google Cloud
gcloud auth login
```

Run the script without arguments and select option 0 to execute all initialization steps sequentially:
```bash
Bash
chmod +x setup.sh
./setup.sh
```
```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID
```

## 2. Update Configuration

Edit `terraform/environments/dev.tfvars`:

```hcl
gcp_project = "YOUR_PROJECT_ID"
gcp_region  = "europe-west1"
```

Update the Cloud Run image URL (or leave as-is for now):

```hcl
cloud_run_image_url = "europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/adk-agent/adk-agent:latest"
```

## 3. Initialize Terraform

```bash
cd terraform_infrastructure
terraform init
```

## 4. Plan Deployment

```bash
terraform plan -var-file=../environments/dev.tfvars
```

Review the output to see what will be created.

## 5. Deploy

```bash
terraform apply -var-file=../environments/dev.tfvars
```

Type `yes` to confirm.

# Populate data sources 
### Populate Data Sources

Before executing the seeding scripts locally, ensure your active GCP identity or service account possesses the necessary access rights. You can grant the required BigQuery permissions via the Google Cloud CLI:

```bash
# Get your active authenticated account
gcloud auth list

# Grant BigQuery Data Editor role
gcloud projects add-iam-policy-binding adk-workshop-sosta-app-dev \
    --member="user:YOUR_EMAIL@gmail.com" \
    --role="roles/bigquery.dataEditor"

```

Once permissions are configured, run the database seeding scripts to populate your Firestore collections and BigQuery tables:

```bash
python seeding/firestore_seed.py
python seeding/bigquery_seed.py
python seeding/firestore_memory_seed.py


```

With the infrastructure provisioned via Terraform and the database seeded with initial knowledge, our agent tools now have real backend services to interact with.