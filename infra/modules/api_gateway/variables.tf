variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "inference_invoke_arn" {
  description = "Lambda invoke ARN for inference function"
  type        = string
}

variable "cloudwatch_log_group_arn" {
  description = "CloudWatch log group ARN for API Gateway access logs"
  type        = string
}
