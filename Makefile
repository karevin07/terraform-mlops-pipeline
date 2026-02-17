# Load environment variables
include .env
export

# Default values if .env is missing or variables are not set
AWS_REGION ?= us-east-1
PROJECT_NAME ?= mlops-platform
ENVIRONMENT ?= dev

# ECR Repo URL construction
ECR_REPO_URL = $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
REPO_NAME = $(PROJECT_NAME)-$(ENVIRONMENT)

# Image Tags
TRAINING_TAG = training-latest
INFERENCE_TAG = inference-latest

.PHONY: help ecr-login build-training push-training build-inference push-inference deploy-images

help: ## Show this help message
	@echo 'Usage:'
	@echo '  make [target]'
	@echo ''
	@echo 'Targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

ecr-login: ## Login to ECR
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REPO_URL)

build-training: ## Build training docker image
	docker build -t $(REPO_NAME):$(TRAINING_TAG) training/

push-training: build-training ## Push training docker image to ECR
	docker tag $(REPO_NAME):$(TRAINING_TAG) $(ECR_REPO_URL)/$(REPO_NAME):$(TRAINING_TAG)
	docker push $(ECR_REPO_URL)/$(REPO_NAME):$(TRAINING_TAG)

build-inference: ## Build inference docker image
	docker build -t $(REPO_NAME):$(INFERENCE_TAG) inference/

push-inference: build-inference ## Push inference docker image to ECR
	docker tag $(REPO_NAME):$(INFERENCE_TAG) $(ECR_REPO_URL)/$(REPO_NAME):$(INFERENCE_TAG)
	docker push $(ECR_REPO_URL)/$(REPO_NAME):$(INFERENCE_TAG)

deploy-images: ecr-login push-training push-inference ## Build and push all images to ECR (Required before Terraform Apply)

tf-init: ## Initialize Terraform
	cd infra && terraform init

tf-plan: ## Plan Terraform changes
	cd infra && terraform plan

tf-apply: ## Apply Terraform changes
	cd infra && terraform apply

tf-destroy: ## Destroy Terraform resources
	cd infra && terraform destroy

cost-estimate: ## Estimate cloud costs using Infracost
	infracost breakdown --path infra/

# --- Data & Training (Local) ---

fetch-data: ## Fetch stock data from Yahoo Finance (Requires S3_RAW_BUCKET)
	uv run scripts/fetch_stock_data.py --tickers 2330.TW 0050.TW QQQ SCHD --bucket $(S3_RAW_BUCKET)

generate-sample-data: ## Generate sample CSV data for local testing
	uv run tests/generate_sample_data.py

test-local-training: generate-sample-data ## Run local training test with mock environment
	export S3_RAW_BUCKET=test-bucket; \
	export S3_MODEL_BUCKET=test-bucket; \
	export DYNAMODB_TABLE=test-table; \
	export AWS_REGION=$(AWS_REGION); \
	uv run tests/test_train_local.py
