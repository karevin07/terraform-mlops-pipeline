# Model Registry Design

This document defines the schema and access patterns for the serverless Model Registry built on DynamoDB.

## DynamoDB Schema

- **Table Name**: `${project}-${env}-model-registry`
- **Partition Key (PK)**: `ModelName` (String) - e.g., `"stock-prediction"`
- **Sort Key (SK)**: `Version` (String) - e.g., `"v20231027120000"`

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `Status` | String | `training`, `staging`, `canary`, `stable`, `archived` |
| `ArtifactUrl` | String | S3 URI to the scikit-learn artifact (e.g., `s3://.../model.joblib`) |
| `OnnxUrl` | String | S3 URI to the ONNX artifact used by inference (e.g., `s3://.../model.onnx`) |
| `Metrics` | String (JSON) | Serialized evaluation metrics (e.g., `{"rmse": 1.23, "mae": 0.98}`) |
| `CreatedAt` | String | ISO 8601 Timestamp |
| `CreatedBy` | String | Optional: User or System ID |
| `Config` | Map | Optional: Hyperparameters used for training |

## Access Patterns

### 1. Register New Model Version
- **Operation**: `PutItem`
- **Input**:
  ```json
  {
    "ModelName": "stock-prediction",
    "Version": "v20231027120000",
    "Status": "training",
    "ArtifactUrl": "s3://bucket/stock-prediction/v20231027120000/model.joblib",
    "OnnxUrl": "s3://bucket/stock-prediction/v20231027120000/model.onnx",
    "Metrics": "{\"rmse\": 1.23, \"mae\": 0.98}",
    "CreatedAt": "2024-03-20T10:00:00Z"
  }
  ```

### 2. Get Specific Model Version
- **Operation**: `GetItem`
- **Key**: `{ "ModelName": "stock-prediction", "Version": "v20231027120000" }`

### 3. List All Versions for a Model
- **Operation**: `Query`
- **KeyConditionExpression**: `ModelName = :name`
- **ScanIndexForward**: `false` (Newest first)

### 4. Promote Model to Canary/Stable
- **Operation**: `UpdateItem`
- **Key**: `{ "ModelName": "stock-prediction", "Version": "v20231027120000" }`
- **UpdateExpression**: `SET Status = :status`
- **ExpressionAttributeValues**: `{ ":status": "canary" }`

### 5. Find Current Stable / Canary Version (Inference)
*Note: Since DynamoDB doesn't natively index non-key attributes efficiently without GSI, for low volume we Query recent versions and filter application-side, or use a GSI on `Status` if scale increases.*

- **Pattern**: Query `ModelName` (Limit 5, descending) → Filter for `Status == 'stable' || Status == 'canary'` → Load `OnnxUrl`.
