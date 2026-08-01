output "training_log_group_name" {
  value = aws_cloudwatch_log_group.training.name
}

output "inference_log_group_name" {
  value = aws_cloudwatch_log_group.inference.name
}

output "api_gateway_log_group_arn" {
  value = aws_cloudwatch_log_group.api_gateway.arn
}
