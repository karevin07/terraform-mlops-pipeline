resource "aws_dynamodb_table" "model_registry" {
  name           = "${var.project_name}-${var.environment}-model-registry"
  billing_mode   = "PAY_PER_REQUEST" # Free Tier friendly for low volume
  hash_key       = "ModelName"
  range_key      = "Version"

  attribute {
    name = "ModelName"
    type = "S"
  }

  attribute {
    name = "Version"
    type = "S"
  }

  tags = {
    Name = "Model Registry"
  }
}
