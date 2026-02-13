variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name, used for tagging and naming resources"
  type        = string
  default     = "mlops-platform"
}

variable "environment" {
  description = "Deployment environment (e.g., dev, prod)"
  type        = string
  default     = "dev"
}

variable "alert_email" {
  description = "Email address for AWS Budget alarm notifications"
  type        = string
}
