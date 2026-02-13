# Model Registry Design

This document defines the schema and access patterns for the serverless Model Registry built on DynamoDB.

## DynamoDB Schema

- **Table Name**: `${project}-${env}-model-registry`
- **Partition Key (PK)**: `ModelName` (String) - e.g., "churn-prediction"
- **Sort Key (SK)**: `Version` (String) - e.g., "v1.0.0", "v1.2.3"

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `Status` | String | `training`, `staging`, `canary`, `stable`, `archived` |
| `ArtifactUrl` | String | S3 URI to the model artifact (e.g., `s3://.../model.tar.gz`) |
| `Metrics` | Map | Key-value pairs of evaluation metrics (e.g., `{"accuracy": 0.95, "f1": 0.92}`) |
| `CreatedAt` | String | ISO 8601 Timestamp |
| `CreatedBy` | String | User or System ID |
| `Config` | Map | Hyperparameters used for training |

## Access Patterns

### 1. Register New Model Version
- **Operation**: `PutItem`
- **Input**:
  ```json
  {
    "ModelName": "churn-prediction",
    "Version": "v1.2.0",
    "Status": "training",
    "CreatedAt": "2024-03-20T10:00:00Z"
  }
  ```

### 2. Get Specific Model Version
- **Operation**: `GetItem`
- **Key**: `{ "ModelName": "churn-prediction", "Version": "v1.2.0" }`

### 3. List All Versions for a Model
- **Operation**: `Query`
- **KeyConditionExpression**: `ModelName = :name`
- **ScanIndexForward**: `false` (Newest first)

### 4. Promote Model to Canary/Stable
- **Operation**: `UpdateItem`
- **Key**: `{ "ModelName": "churn-prediction", "Version": "v1.2.0" }`
- **UpdateExpression**: `SET Status = :status`
- **ExpressionAttributeValues**: `{ ":status": "canary" }`

### 5. Find Current Stable Version
*Note: Since DynamoDB doesn't natively index non-key attributes efficiently without GSI, for low volume we can Query latest versions and filter application-side, or use a GSI on `Status` if scale increases.*

- **Pattern**: Query `ModelName` (Limit 10) -> Filter for `Status == 'stable'` in application logic.
