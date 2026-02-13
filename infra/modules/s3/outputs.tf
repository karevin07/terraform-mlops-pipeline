output "raw_bucket_id" {
  value = aws_s3_bucket.raw_data.id
}

output "feature_bucket_id" {
  value = aws_s3_bucket.feature_data.id
}

output "model_bucket_id" {
  value = aws_s3_bucket.model_artifacts.id
}

output "model_bucket_arn" {
  value = aws_s3_bucket.model_artifacts.arn
}
