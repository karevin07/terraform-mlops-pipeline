output "training_function_name" {
  value = aws_lambda_function.training.function_name
}

output "training_function_arn" {
  value = aws_lambda_function.training.arn
}

output "inference_function_name" {
  value = aws_lambda_function.inference.function_name
}

output "inference_function_arn" {
  value = aws_lambda_function.inference.arn
}

output "inference_invoke_arn" {
  value = aws_lambda_function.inference.invoke_arn
}
