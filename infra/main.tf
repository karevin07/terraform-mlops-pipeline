# Central module orchestration — AWS Free Tier Architecture

# --- Storage ---
module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
}

# --- Model Metadata ---
module "dynamodb" {
  source = "./modules/dynamodb"

  project_name = var.project_name
  environment  = var.environment
}

# --- Container Registry ---
module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

# --- IAM ---
module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
}

# --- Lambda Functions ---
module "lambda" {
  source = "./modules/lambda"

  project_name             = var.project_name
  environment              = var.environment
  lambda_execution_role_arn = module.iam.lambda_execution_role_arn
  ecr_repository_url       = module.ecr.repository_url
  s3_raw_bucket            = module.s3.raw_bucket_id
  s3_feature_bucket        = module.s3.feature_bucket_id
  s3_model_bucket          = module.s3.model_bucket_id
  dynamodb_table_name      = module.dynamodb.table_name
  api_gateway_execution_arn = module.api_gateway.execution_arn
}

# --- API Gateway ---
module "api_gateway" {
  source = "./modules/api_gateway"

  project_name             = var.project_name
  environment              = var.environment
  inference_invoke_arn     = module.lambda.inference_invoke_arn
  cloudwatch_log_group_arn = module.cloudwatch.inference_log_group_arn
}

# --- Monitoring ---
module "cloudwatch" {
  source = "./modules/cloudwatch"

  project_name = var.project_name
  environment  = var.environment
}

# --- Cost Guardrail ---
module "budgets" {
  source = "./modules/budgets"

  project_name = var.project_name
  environment  = var.environment
  alert_email  = var.alert_email
}
