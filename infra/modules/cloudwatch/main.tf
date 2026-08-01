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

resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "training_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-training-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_description   = "Training Lambda reported Errors > 0"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.training_function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "inference_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-inference-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_description   = "Inference Lambda reported Errors > 0"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.inference_function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "inference_duration" {
  alarm_name          = "${var.project_name}-${var.environment}-inference-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Maximum"
  threshold           = 10000 # 10s — soft signal before 30s timeout
  treat_missing_data  = "notBreaching"
  alarm_description   = "Inference Lambda Duration max > 10s"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = var.inference_function_name
  }
}
