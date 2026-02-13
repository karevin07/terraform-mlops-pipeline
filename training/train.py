import os
import boto3
import pandas as pd
import joblib
import json
import logging
from io import BytesIO
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

# Configuration
S3_RAW_BUCKET = os.environ.get("S3_RAW_BUCKET")
S3_FEATURE_BUCKET = os.environ.get("S3_FEATURE_BUCKET")
S3_MODEL_BUCKET = os.environ.get("S3_MODEL_BUCKET")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")
REGION = os.environ.get("AWS_REGION", "us-east-1")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

def load_data(bucket, key="data.csv"):
    logger.info(f"Loading data from s3://{bucket}/{key}")
    obj = s3.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(obj["Body"])

def train_model(df):
    logger.info("Training model...")
    # Minimal example: predict 'target' from other columns
    X = df.drop("target", axis=1)
    y = df["target"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=10, max_depth=5) # Lightweight for Lambda
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    metrics = {
        "accuracy": accuracy_score(y_test, preds),
        "f1": f1_score(y_test, preds, average="weighted")
    }
    
    return model, metrics

def save_model(model, bucket, key):
    logger.info(f"Saving model to s3://{bucket}/{key}")
    buffer = BytesIO()
    joblib.dump(model, buffer)
    buffer.seek(0)
    s3.put_object(Bucket=bucket, Key=key, Body=buffer)

def register_model(model_name, version, metrics, artifact_path):
    logger.info(f"Registering model {model_name}:{version} to DynamoDB")
    item = {
        "ModelName": model_name,
        "Version": version,
        "Status": "training",
        "Metrics": json.dumps(metrics),
        "ArtifactUrl": artifact_path,
        "CreatedAt": datetime.utcnow().isoformat()
    }
    table.put_item(Item=item)

def lambda_handler(event, context):
    try:
        # 1. Load Data
        df = load_data(S3_RAW_BUCKET)
        
        # 2. Train
        model, metrics = train_model(df)
        logger.info(f"Training metrics: {metrics}")
        
        # 3. Save Artifact
        version = datetime.now().strftime("v%Y%m%d%H%M%S")
        model_name = "churn-prediction" # Example
        artifact_key = f"{model_name}/{version}/model.joblib"
        save_model(model, S3_MODEL_BUCKET, artifact_key)
        
        # 4. Register
        register_model(model_name, version, metrics, f"s3://{S3_MODEL_BUCKET}/{artifact_key}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Training successful", "version": version, "metrics": metrics})
        }
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
