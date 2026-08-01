resource "aws_cloudwatch_log_group" "training" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-training"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "inference" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-inference"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}"
  retention_in_days = 7
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${var.environment}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 1
        properties = {
          markdown = "# MLOps Pipeline Dashboard"
        }
      }
    ]
  })
}
