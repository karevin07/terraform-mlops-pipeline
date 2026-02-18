output "inference_api_url" {
  description = "The URL of the Inference API Gateway"
  value       = module.api_gateway.api_endpoint
}

output "training_function_name" {
  description = "The name of the Training Lambda function"
  value       = module.lambda.training_function_name
}

output "inference_function_name" {
  description = "The name of the Inference Lambda function"
  value       = module.lambda.inference_function_name
}
