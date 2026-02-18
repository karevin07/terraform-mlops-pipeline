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

##@ Setup
.PHONY: install format test docker clean help

install: ## Install dependencies (Python & Go)
	@echo "Installing Python dependencies..."
	@uv sync
	@echo "Installing Go dependencies..."
	@cd inference && go mod download

format: ## Format code (Python & Go)
	@echo "Formatting Go code..."
	@cd inference && go fmt ./...
	@echo "Formatting Python code..."
	@uv run ruff format . || echo "Ruff not found, skipping"

test: test-local-training test-local-inference ## Run all local tests

##@ Infrastructure
tf-init: ## Initialize Terraform
	cd infra && terraform init

tf-plan: ## Plan Terraform changes
	cd infra && terraform plan

tf-apply: ## Apply Terraform changes
	cd infra && terraform apply

tf-destroy: ## Destroy Terraform resources
	cd infra && terraform destroy

cost-estimate: ## Estimate monthly cloud costs using Infracost
	infracost breakdown --path infra/

##@ Docker
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

deploy-images: ecr-login push-training push-inference ## Build and push all images to ECR

deploy-inference-lambda: ## Update Lambda function with latest inference image
	@echo "Retrieving configuration..."
	@FUNCTION_NAME=$$(cd infra && terraform output -raw inference_function_name); \
	if [ -z "$$FUNCTION_NAME" ] || echo "$$FUNCTION_NAME" | grep -q "No outputs found"; then \
		echo "Error: Could not get inference_function_name from Terraform."; \
		echo "Please run 'make tf-apply' to update your Terraform state."; \
		exit 1; \
	fi; \
	REPO_URI=$$(aws ecr describe-repositories --repository-name $(REPO_NAME) --query 'repositories[0].repositoryUri' --output text); \
	echo "Updating Lambda function: $$FUNCTION_NAME with image: $$REPO_URI:$(INFERENCE_TAG)..."; \
	aws lambda update-function-code \
		--function-name $$FUNCTION_NAME \
		--image-uri $$REPO_URI:$(INFERENCE_TAG) \
		--region $(AWS_REGION)

##@ Data & Training
fetch-data: ## Fetch stock data from Yahoo Finance
	uv run scripts/fetch_stock_data.py --tickers 2330.TW 0050.TW QQQ SCHD --bucket $(S3_RAW_BUCKET)

generate-sample-data: ## Generate sample CSV data for local testing
	uv run tests/generate_sample_data.py

generate-sample-model: ## Generate sample ONNX model for local testing
	uv run scripts/debug_train_and_export.py

test-local-training: generate-sample-data ## Run local training test with mock environment
	export S3_RAW_BUCKET=test-bucket; \
	export S3_MODEL_BUCKET=test-bucket; \
	export DYNAMODB_TABLE=test-table; \
	export AWS_REGION=$(AWS_REGION); \
	uv run --extra training tests/test_train_local.py

##@ Verification
test-local-inference: build-inference generate-sample-model ## Run local inference container and test with curl
	@echo "Starting inference container..."
	@docker run -d --rm -p 8080:8080 --name inference-local -v $$(pwd)/model.onnx:/model.onnx -e LOCAL_MODEL_PATH=/model.onnx $(REPO_NAME):$(INFERENCE_TAG)
	@echo "Waiting for container to start..."
	@sleep 5
	@echo "Sending test request..."
	@curl -s -X POST http://localhost:8080/predict -d '{"features": [0.1, 0.2, 0.3, 0.4]}' | jq .
	@echo "\nStopping container..."
	@docker stop inference-local

predict-lambda: ## Send a test request to the deployed Lambda Inference API
	@echo "Invoking Inference API..."
	@API_URL=$$(cd infra && terraform output -raw inference_api_url); \
	if [ -z "$$API_URL" ] || echo "$$API_URL" | grep -q "No outputs found"; then \
		echo "Error: Could not get inference_api_url from Terraform."; \
		echo "Please run 'make tf-apply' to update your Terraform state."; \
		exit 1; \
	fi; \
	echo "API URL: $$API_URL/predict"; \
	curl -s -X POST "$$API_URL/predict" \
		-H "Content-Type: application/json" \
		-d '{"features": [150.5, 65.2, 148.0, 5000000.0]}' | jq .

logs-training: ## Show recent CloudWatch logs for Training Lambda
	aws logs tail /aws/lambda/$(PROJECT_NAME)-$(ENVIRONMENT)-training --since 1h

check-model: ## List model artifacts in S3 Model Bucket
	aws s3 ls s3://$(S3_MODEL_BUCKET)/stock-prediction/ --recursive --human-readable --summarize

check-metadata: ## Scan DynamoDB for training results
	aws dynamodb scan \
		--table-name $(DYNAMODB_TABLE) \
		--expression-attribute-names '{"#S": "Status"}' \
		--expression-attribute-values '{":v": {"S": "training"}}' \
		--filter-expression "#S = :v" \
		--output json

##@ Help
help:  ## display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help
