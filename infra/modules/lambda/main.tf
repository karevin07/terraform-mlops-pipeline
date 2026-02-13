# --- Training Lambda ---
resource "aws_lambda_function" "training" {
  function_name = "${var.project_name}-${var.environment}-training"
  role          = var.lambda_execution_role_arn
  package_type  = "Image"
  image_uri     = "${var.ecr_repository_url}:training-latest"
  timeout       = 900 # 15 min max — cost guardrail
  memory_size   = 512 # Keep low for Free Tier

  environment {
    variables = {
      S3_RAW_BUCKET     = var.s3_raw_bucket
      S3_FEATURE_BUCKET = var.s3_feature_bucket
      S3_MODEL_BUCKET   = var.s3_model_bucket
      DYNAMODB_TABLE    = var.dynamodb_table_name
      ENVIRONMENT       = var.environment
    }
  }

  tags = {
    Name = "Training Job"
    Cost = "free-tier"
  }
}

# --- Inference Lambda ---
resource "aws_lambda_function" "inference" {
  function_name = "${var.project_name}-${var.environment}-inference"
  role          = var.lambda_execution_role_arn
  package_type  = "Image"
  image_uri     = "${var.ecr_repository_url}:inference-latest"
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      S3_MODEL_BUCKET = var.s3_model_bucket
      DYNAMODB_TABLE  = var.dynamodb_table_name
      ENVIRONMENT     = var.environment
    }
  }

  tags = {
    Name = "Inference API"
    Cost = "free-tier"
  }
}

# --- Canary Alias (weighted routing) ---
resource "aws_lambda_alias" "inference_stable" {
  name             = "stable"
  function_name    = aws_lambda_function.inference.function_name
  function_version = aws_lambda_function.inference.version

  lifecycle {
    ignore_changes = [function_version, routing_config]
  }
}

resource "aws_lambda_function_event_invoke_config" "inference" {
  function_name = aws_lambda_function.inference.function_name

  maximum_retry_attempts       = 0
  maximum_event_age_in_seconds = 60
}

# Permission for API Gateway to invoke inference Lambda
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.inference.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}
