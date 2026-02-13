output "training_log_group_name" {
  value = aws_cloudwatch_log_group.training.name
}

output "inference_log_group_name" {
  value = aws_cloudwatch_log_group.inference.name
}

output "inference_log_group_arn" {
  value = aws_cloudwatch_log_group.inference.arn
}
