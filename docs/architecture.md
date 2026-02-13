# Architecture Documentation

[English](architecture.md) | [繁體中文](architecture_zh-TW.md)

This document details the architecture of the Serverless MLOps pipeline on AWS Free Tier.

## High-Level Architecture

The pipeline is entirely serverless to maximize cost efficency (Free Tier eligible).

```mermaid
graph TD
    User[User / Client] -->|HTTPS| APIGW[API Gateway]
    
    subgraph "Inference (Serverless)"
        APIGW -->|Proxy| InferenceLambda[Inference Lambda<br/> Python + Scikit-Learn]
        InferenceLambda -->|Load Model| S3[S3 Bucket<br/> Model Artifacts]
        InferenceLambda -->|Get Metadata| DDB[DynamoDB<br/> Model Registry]
    end

    subgraph "Training (Serverless)"
        Trigger[Event / Schedule] --> TrainingLambda[Training Lambda<br/> Python + Scikit-Learn]
        TrainingLambda -->|Pull Data| S3
        TrainingLambda -->|Save Model| S3
        TrainingLambda -->|Register Model| DDB
        TrainingLambda -->|Logs| CW[CloudWatch Logs]
    end

    subgraph "CI/CD (GitHub Actions)"
        Git[GitHub Repo] -->|Push Tag| Action[GitHub Action]
        Action -->|Terraform| Infra[AWS Infrastructure]
        Action -->|Docker Build| ECR[Amazon ECR]
        ECR -->|Image Update| InferenceLambda
        ECR -->|Image Update| TrainingLambda
    end

    style APIGW fill:#f9f,stroke:#333
    style InferenceLambda fill:#bbf,stroke:#333
    style TrainingLambda fill:#bfb,stroke:#333
    style S3 fill:#fdcb6e,stroke:#333
    style DDB fill:#fdcb6e,stroke:#333
```

## Component Details

### 1. Infrastructure (Terraform)
*   **State Management**: Local state (for simplicity) or S3 remote state.
*   **Modules**:
    *   `s3`: Stores training data and model artifacts (`.joblib`).
    *   `dynamodb`: Stores model metadata (metrics, version, lineage).
    *   `lambda`: Python container images for Training and Inference.
    *   `api_gateway`: Exposes the Inference Lambda via HTTP API.
    *   `ecr`: Stores Docker container images.
    *   `iam`: Least-privilege roles for execution.
    *   `budgets`: Cost guardrails ($0.01 limit).

### 2. Training Pipeline
*   **Compute**: AWS Lambda (Container Image).
*   **Image**: Python 3.9 base, includes `scikit-learn`, `pandas`, `boto3`.
*   **Process**:
    1.  Fetch dataset from S3.
    2.  Train Random Forest model.
    3.  Evaluate metrics (Accuracy, F1).
    4.  Save model artifact to S3 (`models/vX.Y.Z/model.joblib`).
    5.  Log metadata to DynamoDB.

### 3. Model Registry
*   **Storage**: S3 for large files (weights), DynamoDB for metadata.
*   **Versioning**: Semantic versioning managed via DynamoDB items.

### 4. Inference API
*   **Compute**: AWS Lambda (Container Image) optimized for low latency.
*   **Routing**: AWS API Gateway (HTTP API).
*   **Flow**:
    1.  Receives JSON payload.
    2.  Loads model from S3 (cached in `/tmp` for warm starts).
    3.  Returns prediction.
