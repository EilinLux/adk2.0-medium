#!/bin/bash
set -e

# ==========================================
# ADK AGENT TERRAFORM SETUP SCRIPT
# ==========================================
# This script helps with initial setup and deployment

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==========================================
# HELPER FUNCTIONS
# ==========================================

print_header() {
    echo -e "\n${BLUE}=====================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=====================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# ==========================================
# CHECKS
# ==========================================

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform not found. Install from https://www.terraform.io/downloads"
        exit 1
    fi
    TF_VERSION=$(terraform version | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    print_success "Terraform found: $TF_VERSION"

    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud SDK not found. Install from https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    print_success "Google Cloud SDK found"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found. You'll need it to build container images."
    else
        print_success "Docker found"
    fi

    # Check Make
    if ! command -v make &> /dev/null; then
        print_warning "Make not found. You can still use terraform directly."
    else
        print_success "Make found"
    fi
}

# ==========================================
# AUTHENTICATION
# ==========================================

setup_gcp_auth() {
    print_header "Setting Up GCP Authentication"

    # Check if already authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
        print_success "Already authenticated as: $ACCOUNT"
        read -p "Use this account? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            gcloud auth login
        fi
    else
        print_info "No active authentication found. Starting login..."
        gcloud auth login
    fi

    # Get project ID
    PROJECT=$(gcloud config get-value project)
    if [ -z "$PROJECT" ]; then
        print_error "No default project set"
        read -p "Enter your GCP Project ID: " PROJECT
        gcloud config set project $PROJECT
    fi

    print_success "Using project: $PROJECT"
}

# ==========================================
# SERVICE ACCOUNT SETUP
# ==========================================

setup_service_account() {
    print_header "Setting Up Terraform Service Account"

    PROJECT=$(gcloud config get-value project)

    # Check if service account exists
    if gcloud iam service-accounts describe terraform-admin@${PROJECT}.iam.gserviceaccount.com &> /dev/null; then
        print_warning "Service account 'terraform-admin' already exists"
        read -p "Use existing service account? [Y/n]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            return
        fi
    else
        print_info "Creating service account 'terraform-admin'..."
        gcloud iam service-accounts create terraform-admin \
            --display-name="Terraform Admin" \
            --project=$PROJECT
        print_success "Service account created"
    fi

    # Grant roles
    print_info "Granting IAM roles..."

    ROLES=(
        "roles/editor"
        "roles/iam.securityAdmin"
        "roles/compute.admin"
        "roles/run.admin"
        "roles/bigquery.admin"
        "roles/datastore.admin"
        "roles/serviceusage.admin"
    )

    for role in "${ROLES[@]}"; do
        gcloud projects add-iam-policy-binding $PROJECT \
            --member="serviceAccount:terraform-admin@${PROJECT}.iam.gserviceaccount.com" \
            --role="$role" \
            --condition=None \
            2>/dev/null || true
    done

    print_success "IAM roles granted"
    print_info "Service account ready: terraform-admin@${PROJECT}.iam.gserviceaccount.com"
}

# ==========================================
# INITIALIZE TERRAFORM
# ==========================================

initialize_terraform() {
    print_header "Initializing Terraform"

    cd terraform_infrastructure

    # Check if already initialized
    if [ -d ".terraform" ]; then
        print_warning "Terraform already initialized"
        read -p "Re-initialize? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            cd ..
            return
        fi
    fi

    print_info "Running terraform init..."
    terraform init -upgrade

    print_success "Terraform initialized"
    cd ..
}

# ==========================================
# VALIDATION
# ==========================================

validate_configuration() {
    print_header "Validating Terraform Configuration"

    cd terraform_infrastructure

    print_info "Running terraform validate..."
    terraform validate

    print_info "Checking formatting..."
    terraform fmt -check -recursive . || {
        read -p "Fix formatting? [Y/n]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            terraform fmt -recursive .
            print_success "Formatting fixed"
        fi
    }

    cd ..
}

# ==========================================
# CONFIGURATION SETUP
# ==========================================

setup_configuration() {
    print_header "Configuring Environment Variables"

    PROJECT=$(gcloud config get-value project)
    REGION=$(gcloud config get-value compute/region || echo "europe-west1")

    print_info "Update environments/dev.tfvars with your settings:"
    print_info "  Project ID: $PROJECT"
    print_info "  Region: $REGION"

    # Check if tfvars files exist
    if [ ! -f "environments/dev.tfvars" ]; then
        print_error "environments/dev.tfvars not found!"
        return
    fi

    # Update project ID in tfvars files
    sed -i '' "s|gcp_project = \".*\"|gcp_project = \"$PROJECT\"|g" environments/*.tfvars

    print_success "Configuration updated"
}

# ==========================================
# DOCKER SETUP
# ==========================================

setup_docker_registry() {
    print_header "Setting Up Artifact Registry"

    PROJECT=$(gcloud config get-value project)
    REGION=${1:-europe-west1}

    # Check if repository exists
    if gcloud artifacts repositories describe adk-agent --location=$REGION &>/dev/null; then
        print_warning "Artifact Registry repository 'adk-agent' already exists"
        return
    fi

    print_info "Creating Artifact Registry repository..."
    gcloud artifacts repositories create adk-agent \
        --repository-format=docker \
        --location=$REGION \
        --description="ADK Agent Docker images" \
        --project=$PROJECT

    print_success "Artifact Registry repository created"

    # Configure Docker auth
    print_info "Configuring Docker authentication..."
    gcloud auth configure-docker ${REGION}-docker.pkg.dev

    print_success "Docker registry ready"
    print_info "Repository: ${REGION}-docker.pkg.dev/${PROJECT}/adk-agent"
}

# ==========================================
# REMOTE STATE SETUP
# ==========================================

setup_remote_state() {
    print_header "Setting Up Remote Terraform State"

    PROJECT=$(gcloud config get-value project)
    BUCKET="terraform-state-${PROJECT}"

    # Check if bucket exists
    if gsutil ls gs://${BUCKET} &>/dev/null; then
        print_warning "GCS bucket '$BUCKET' already exists"
        return
    fi

    print_info "Creating GCS bucket for remote state..."
    gsutil mb gs://${BUCKET}

    # Enable versioning
    print_info "Enabling versioning..."
    gsutil versioning set on gs://${BUCKET}

    print_success "Remote state bucket created: gs://${BUCKET}"
    print_info "Update terraform.tf to use remote state:"
    print_info "  backend \"gcs\" {"
    print_info "    bucket = \"$BUCKET\""
    print_info "    prefix = \"adk-agent/\""
    print_info "  }"
}

# ==========================================
# DEPLOYMENT PREVIEW
# ==========================================

preview_deployment() {
    print_header "Preview Deployment"

    cd terraform_infrastructure

    read -p "Enter environment (dev/staging/prod) [dev]: " ENV
    ENV=${ENV:-dev}

    if [ ! -f "../environments/${ENV}.tfvars" ]; then
        print_error "Configuration file not found: environments/${ENV}.tfvars"
        cd ..
        return
    fi

    print_info "Planning ${ENV} deployment..."
    terraform plan -var-file=../environments/${ENV}.tfvars

    cd ..
}

# ==========================================
# MAIN MENU
# ==========================================

show_menu() {
    echo -e "\n${BLUE}ADK Agent Terraform Setup${NC}\n"
    echo "1) Check Prerequisites"
    echo "2) Setup GCP Authentication"
    echo "3) Create Service Account"
    echo "4) Initialize Terraform"
    echo "5) Validate Configuration"
    echo "6) Setup Configuration Files"
    echo "7) Setup Artifact Registry"
    echo "8) Setup Remote State"
    echo "9) Preview Deployment"
    echo "0) Run Complete Setup (all steps)"
    echo -e "\nSelect option [0-9]: "
}

run_complete_setup() {
    print_header "Running Complete Setup"

    check_prerequisites
    setup_gcp_auth
    setup_service_account
    setup_configuration
    initialize_terraform
    validate_configuration
    setup_docker_registry
    setup_remote_state

    print_header "Setup Complete!"
    print_success "Terraform is ready for deployment"
    print_info "Next steps:"
    print_info "  1. Review environments/dev.tfvars"
    print_info "  2. Build and push Docker image: make docker-push"
    print_info "  3. Deploy: make apply ENV=dev"
}

# ==========================================
# MAIN
# ==========================================

main() {
    if [ "$#" -eq 0 ]; then
        # Interactive mode
        while true; do
            show_menu
            read -r choice

            case $choice in
                1) check_prerequisites ;;
                2) setup_gcp_auth ;;
                3) setup_service_account ;;
                4) initialize_terraform ;;
                5) validate_configuration ;;
                6) setup_configuration ;;
                7) setup_docker_registry ;;
                8) setup_remote_state ;;
                9) preview_deployment ;;
                0) run_complete_setup; break ;;
                *) print_error "Invalid option" ;;
            esac
        done
    else
        # Command line mode
        case "$1" in
            all) run_complete_setup ;;
            check) check_prerequisites ;;
            auth) setup_gcp_auth ;;
            sa) setup_service_account ;;
            init) initialize_terraform ;;
            validate) validate_configuration ;;
            config) setup_configuration ;;
            docker) setup_docker_registry ;;
            state) setup_remote_state ;;
            preview) preview_deployment ;;
            *)
                echo "Usage: $0 [all|check|auth|sa|init|validate|config|docker|state|preview]"
                echo "  all      - Run complete setup"
                echo "  check    - Check prerequisites"
                echo "  auth     - Setup GCP authentication"
                echo "  sa       - Create service account"
                echo "  init     - Initialize Terraform"
                echo "  validate - Validate configuration"
                echo "  config   - Setup configuration files"
                echo "  docker   - Setup Artifact Registry"
                echo "  state    - Setup remote state"
                echo "  preview  - Preview deployment"
                ;;
        esac
    fi
}

main "$@"
