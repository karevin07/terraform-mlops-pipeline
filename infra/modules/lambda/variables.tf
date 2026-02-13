variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "lambda_execution_role_arn" {
  description = "IAM role ARN for Lambda execution"
  type        = string
}

variable "ecr_repository_url" {
  description = "ECR repository URL for Lambda container images"
  type        = string
}

variable "s3_raw_bucket" {
  type = string
}

variable "s3_feature_bucket" {
  type = string
}

variable "s3_model_bucket" {
  type = string
}

variable "dynamodb_table_name" {
  type = string
}

variable "api_gateway_execution_arn" {
  description = "API Gateway execution ARN for Lambda permission"
  type        = string
}
