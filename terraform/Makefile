.PHONY: help init plan apply destroy fmt validate lint test clean

# Default environment
ENV ?= dev

# Terraform directory
TF_DIR := terraform_infrastructure

help:
	@echo "ADK Agent Terraform Management"
	@echo "=============================="
	@echo ""
	@echo "Usage: make [target] [ENV=dev|staging|prod]"
	@echo ""
	@echo "Targets:"
	@echo "  init       - Initialize Terraform (required first step)"
	@echo "  plan       - Show what changes will be made"
	@echo "  apply      - Apply changes to infrastructure"
	@echo "  destroy    - Destroy infrastructure (use with caution!)"
	@echo "  fmt        - Format Terraform files"
	@echo "  validate   - Validate Terraform configuration"
	@echo "  lint       - Lint Terraform files (requires tflint)"
	@echo "  clean      - Remove .terraform directory and lock files"
	@echo "  output     - Show Terraform outputs"
	@echo "  refresh    - Refresh Terraform state"
	@echo ""
	@echo "Examples:"
	@echo "  make init ENV=dev              # Initialize dev environment"
	@echo "  make plan ENV=staging          # Plan staging deployment"
	@echo "  make apply ENV=prod            # Apply production deployment"
	@echo ""

init:
	@echo "Initializing Terraform for $(ENV) environment..."
	cd $(TF_DIR) && terraform init -upgrade

plan:
	@echo "Planning Terraform changes for $(ENV) environment..."
	cd $(TF_DIR) && terraform plan -var-file=../environments/$(ENV).tfvars -out=tfplan_$(ENV)

apply:
	@echo "Applying Terraform changes for $(ENV) environment..."
	@echo "WARNING: You are about to modify infrastructure for: $(ENV)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd $(TF_DIR) && terraform apply -var-file=../environments/$(ENV).tfvars; \
	else \
		echo "Aborted."; \
	fi

destroy:
	@echo "WARNING: You are about to DESTROY infrastructure for: $(ENV)"
	@echo "This action cannot be undone!"
	@read -p "Type 'destroy-$(ENV)' to confirm: " confirmation; \
	if [ "$$confirmation" = "destroy-$(ENV)" ]; then \
		cd $(TF_DIR) && terraform destroy -var-file=../environments/$(ENV).tfvars; \
	else \
		echo "Aborted."; \
	fi

fmt:
	@echo "Formatting Terraform files..."
	cd $(TF_DIR) && terraform fmt -recursive

validate:
	@echo "Validating Terraform configuration..."
	cd $(TF_DIR) && terraform validate

lint:
	@echo "Linting Terraform files..."
	@command -v tflint >/dev/null 2>&1 || { echo "tflint not found. Install it with: brew install tflint"; exit 1; }
	cd $(TF_DIR) && tflint --init && tflint

clean:
	@echo "Cleaning up Terraform files..."
	cd $(TF_DIR) && rm -rf .terraform .terraform.lock.hcl tfplan_* terraform.tfstate* .terraform.tfvars

output:
	@echo "Terraform outputs for $(ENV) environment..."
	cd $(TF_DIR) && terraform output -var-file=../environments/$(ENV).tfvars

refresh:
	@echo "Refreshing Terraform state for $(ENV) environment..."
	cd $(TF_DIR) && terraform refresh -var-file=../environments/$(ENV).tfvars

# Build and push linux/amd64 Docker image to Artifact Registry (from repository root ..)
docker-build:
	@echo "Building linux/amd64 Docker image for ADK Agent Stack..."
	docker build --platform linux/amd64 -t adk-agent:latest ..

docker-push: docker-build
	@echo "Tagging and pushing Docker image to Artifact Registry..."
	docker tag adk-agent:latest europe-west1-docker.pkg.dev/adk-workshop-sosta-app-dev/adk-agent/adk-agent:latest
	docker push europe-west1-docker.pkg.dev/adk-workshop-sosta-app-dev/adk-agent/adk-agent:latest


# Create GCS bucket for remote state
setup-remote-state:
	@echo "Setting up remote Terraform state..."
	@read -p "Enter GCP project ID: " project_id; \
	gsutil mb gs://terraform-state-$$project_id || true; \
	gsutil versioning set on gs://terraform-state-$$project_id; \
	@echo "Remote state bucket created. Update terraform.tf to use it."
