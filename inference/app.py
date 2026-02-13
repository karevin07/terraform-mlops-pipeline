import os
import boto3
import joblib
import json
import logging
from io import BytesIO

# Configuration
S3_MODEL_BUCKET = os.environ.get("S3_MODEL_BUCKET")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")
REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_NAME = "churn-prediction"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

# Global model cache to leverage Lambda warm start
model_cache = None
model_version = None

def get_latest_stable_version(model_name):
    # In a real scenario, use GSI or query properly. For demo/MVP:
    # Query latest 10 versions and find the first one with Status='stable'
    response = table.query(
        KeyConditionExpression="ModelName = :name",
        ExpressionAttributeValues={":name": model_name},
        ScanIndexForward=False, # Newest first
        Limit=10
    )
    for item in response.get("Items", []):
        if item.get("Status") == "stable" or item.get("Status") == "canary":
             return item
    return None # Fallback or error

def load_model(bucket, key):
    logger.info(f"Loading model from s3://{bucket}/{key}")
    obj = s3.get_object(Bucket=bucket, Key=key)
    return joblib.load(BytesIO(obj["Body"].read()))

def lambda_handler(event, context):
    global model_cache, model_version
    
    # Check for health check
    if event.get("rawPath") == "/health":
         return {"statusCode": 200, "body": "OK"}

    try:
        # 1. Resolve Model Version (if not cached or forced refresh)
        # For MVP: simple caching strategy
        if model_cache is None:
            metadata = get_latest_stable_version(MODEL_NAME)
            if not metadata:
                return {"statusCode": 503, "body": "No stable model found"}
            
            artifact_url = metadata["ArtifactUrl"] # e.g., s3://bucket/key
            # Parse key from s3://bucket/key
            key = artifact_url.replace(f"s3://{S3_MODEL_BUCKET}/", "")
            
            model_cache = load_model(S3_MODEL_BUCKET, key)
            model_version = metadata["Version"]
            logger.info(f"Model {MODEL_NAME}:{model_version} loaded")

        # 2. Parse Input
        body = json.loads(event.get("body", "{}"))
        features = body.get("features")
        if not features:
            return {"statusCode": 400, "body": "Missing 'features' in body"}
        
        # 3. Predict
        prediction = model_cache.predict([features])
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "prediction": int(prediction[0]),
                "model_version": model_version
            })
        }
            
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
