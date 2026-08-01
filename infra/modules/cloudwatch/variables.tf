variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "alert_email" {
  description = "Email for CloudWatch alarm notifications"
  type        = string
}

variable "training_function_name" {
  description = "Training Lambda function name (for metric dimensions)"
  type        = string
}

variable "inference_function_name" {
  description = "Inference Lambda function name (for metric dimensions)"
  type        = string
}
