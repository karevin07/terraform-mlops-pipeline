
import os
import boto3
import pandas as pd
import numpy as np
import joblib
import json
import logging
from io import BytesIO
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator

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

def feature_engineering(df):
    """
    Generate technical indicators and lag features for each ticker.
    """
    logger.info("Starting feature engineering...")
    
    # Ensure data is sorted by Ticker and Date
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by=['Ticker', 'Date'])
    
    # List to store processed dataframes
    processed_dfs = []
    
    # Group by Ticker to avoid data leakage between stocks
    for ticker, group in df.groupby('Ticker'):
        group = group.copy()
        
        # 1. Technical Indicators
        # SMA 20
        sma = SMAIndicator(close=group["Close"], window=20, fillna=True)
        group["SMA_20"] = sma.sma_indicator()
        
        # RSI 14
        rsi = RSIIndicator(close=group["Close"], window=14, fillna=True)
        group["RSI_14"] = rsi.rsi()
        
        # 2. Lag Features (Previous Day's Close)
        group["Lag_Close_1"] = group["Close"].shift(1)
        group["Lag_Volume_1"] = group["Volume"].shift(1)
        
        # 3. Target: Predict Next Day's Close
        group["Target"] = group["Close"].shift(-1)
        
        # Drop rows with NaN (due to shift/indicators)
        group = group.dropna()
        
        processed_dfs.append(group)
        
    return pd.concat(processed_dfs)

def train_model(df):
    logger.info("Training model...")
    
    # Features to use for training
    features = ["SMA_20", "RSI_14", "Lag_Close_1", "Lag_Volume_1"]
    
    X = df[features]
    y = df["Target"]
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False) # Time-series split (no shuffle ideally, but simple split here)
    
    # RandomForestRegressor
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    
    # Evaluation Metrics
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    mae = mean_absolute_error(y_test, preds)
    
    metrics = {
        "rmse": float(rmse),
        "mae": float(mae)
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
        # Check if triggered by S3 Event
        if "Records" in event and event["Records"][0]["eventSource"] == "aws:s3":
            bucket = event["Records"][0]["s3"]["bucket"]["name"]
            key = event["Records"][0]["s3"]["object"]["key"]
            logger.info(f"Triggered by S3 event: s3://{bucket}/{key}")
        else:
            # Fallback for manual invocation (e.g. Test)
            bucket = S3_RAW_BUCKET
            key = "data.csv"
            logger.info(f"Triggered manually, using default: s3://{bucket}/{key}")

        # 1. Load Data
        df = load_data(bucket, key)
        
        # 2. Feature Engineering
        df_processed = feature_engineering(df)
        
        if df_processed.empty:
            raise ValueError("No data available for training after feature engineering")

        # 3. Train
        model, metrics = train_model(df_processed)
        logger.info(f"Training metrics: {metrics}")
        
        # 4. Save Artifact
        version = datetime.now().strftime("v%Y%m%d%H%M%S")
        model_name = "stock-prediction" 
        artifact_key = f"{model_name}/{version}/model.joblib"
        save_model(model, S3_MODEL_BUCKET, artifact_key)
        
        # 5. Register
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
