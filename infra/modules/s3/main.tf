resource "aws_s3_bucket" "raw_data" {
  bucket = "${var.project_name}-${var.environment}-raw-data"
  force_destroy = true 

  tags = {
    Name = "Raw Data"
  }
}

resource "aws_s3_bucket" "feature_data" {
  bucket = "${var.project_name}-${var.environment}-feature-store"
  force_destroy = true

  tags = {
    Name = "Feature Store"
  }
}

resource "aws_s3_bucket" "model_artifacts" {
  bucket = "${var.project_name}-${var.environment}-model-artifacts"
  force_destroy = true

  tags = {
    Name = "Model Artifacts"
  }
}

resource "aws_s3_bucket_versioning" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "model_lifecycle" {
  bucket = aws_s3_bucket.model_artifacts.id

  rule {
    id = "cleanup-old-models"

    filter {} # Apply to all objects

    expiration {
      days = 30
    }

    status = "Enabled"
  }
}
