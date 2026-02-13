output "api_endpoint" {
  value = aws_apigatewayv2_api.main.api_endpoint
}

output "execution_arn" {
  value = aws_apigatewayv2_api.main.execution_arn
}
