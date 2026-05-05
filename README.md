# terraform-mlops-pipeline


![Terraform](https://img.shields.io/badge/Terraform-6222CC?style=for-the-badge&logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Bash](https://img.shields.io/badge/Bash-4EAA25?style=for-the-badge&logo=gnu-bash&logoColor=white)
![Markdown](https://img.shields.io/badge/Markdown-000000?style=for-the-badge&logo=markdown&logoColor=white)

[English](README.md) | [繁體中文](README_zh-TW.md)

## 🎯 Project Positioning

> **Built an end-to-end MLOps pipeline on AWS (Free Tier) using Terraform, enabling automated training, evaluation, model registry, canary deployment, and rollback with cost guardrails.**

## 📦 Architecture

```mermaid
flowchart TB
    subgraph Dev["Developer / CI"]
        DEV[Developer]
        GH[GitHub Actions]
    end

    subgraph AWS["AWS Free Tier"]
        subgraph Storage["Storage"]
            S3_RAW[S3 - Raw Data]
            S3_FEATURE[S3 - Feature Data]
            S3_MODEL[S3 - Model Artifacts]
        end

        subgraph Compute["Serverless Compute"]
            LAMBDA_TRAIN[Lambda - Training Job<br/>Python]
            LAMBDA_INFER[Lambda - Inference API<br/>Python]
        end

        subgraph Registry["Model Registry"]
            DDB[DynamoDB<br/>Model Metadata]
        end

        subgraph Gateway["API Layer"]
            APIGW[API Gateway HTTP<br/>POST /predict<br/>GET /health]
        end

        subgraph Observability["Monitoring & Cost"]
            CW[CloudWatch<br/>Logs / Metrics]
            BUDGET[AWS Budgets<br/>$0.01 Alarm]
        end

        subgraph Container["Container Registry"]
            ECR[ECR<br/>Lambda Images]
        end
    end

    DEV --> GH
    GH -->|terraform apply| AWS
    GH -->|trigger retrain| LAMBDA_TRAIN

    S3_RAW --> LAMBDA_TRAIN
    LAMBDA_TRAIN --> S3_FEATURE
    LAMBDA_TRAIN --> S3_MODEL
    LAMBDA_TRAIN --> DDB

    DDB --> LAMBDA_INFER
    S3_MODEL --> LAMBDA_INFER

    APIGW --> LAMBDA_INFER

    ECR --> LAMBDA_TRAIN
    ECR --> LAMBDA_INFER

    LAMBDA_TRAIN --> CW
    LAMBDA_INFER --> CW
```

## 💰 Free Tier Compliance

| Service | Free Tier Limit | Expected Usage | Status |
|---------|----------------|----------------|--------|
| S3 | 5GB storage, 20K GET/mo | ~100MB | ✅ |
| DynamoDB | 25GB, 25 WCU/RCU | ~1MB | ✅ |
| Lambda | 1M req + 400K GB-s/mo | ~100 req | ✅ |
| API Gateway | 1M calls/mo (12mo) | ~100 calls | ✅ |
| CloudWatch | 10 metrics, 5GB logs | Minimal | ✅ |
| ECR | 500MB storage | ~200MB | ✅ |

### Cost Guardrails
- **AWS Budgets**: $0.01 threshold alarm with email notification
- **ECR Lifecycle**: Keep only last 5 images
- **S3 Lifecycle**: Auto-delete model artifacts after 30 days
- **Lambda Limits**: Training timeout 15min, memory capped
- **Terraform Configuration**: `infra/` (See [Setup Guide](docs/terraform.md))
- **Terraform Tags**: All resources tagged with `Project` + `Environment`

## 🚀 Core Features

1. **Feature pipeline (Python)**: Lambda-based feature engineering
2. **Automated training**: Lambda with 15-min timeout
3. **Model registry**: DynamoDB metadata + S3 artifacts (versioned)
4. **Inference API**: Lambda behind API Gateway
5. **Canary deployment**: Lambda alias weighted routing
6. **Model rollback**: Update DynamoDB metadata — no redeploy needed
7. **Infra as Code**: Terraform modular design
8. **Cost guardrails**: AWS Budgets alarm at $0.01

## 🛠 Tech Stack

- **Infrastructure**: Terraform, AWS (Free Tier)
- **ML/Data**: Python (Pandas, Scikit-learn)
- **Serving**: Python Lambda (container image)
- **CI/CD**: GitHub Actions
- **Database**: DynamoDB (Metadata), S3 (Artifacts)

## 📂 Project Structure

```text
terraform-mlops-pipeline/
├── infra/                  # Terraform
│   ├── modules/
│   │   ├── s3/             # Raw, Feature, Model buckets
│   │   ├── dynamodb/       # Model registry table
│   │   ├── lambda/         # Training + Inference functions
│   │   ├── api_gateway/    # HTTP API
│   │   ├── ecr/            # Container registry
│   │   ├── iam/            # Least-privilege roles
│   │   ├── cloudwatch/     # Logs & metrics
│   │   └── budgets/        # Cost alarm
│   ├── envs/
│   │   ├── dev/
│   │   └── prod/
│   ├── main.tf
│   ├── variables.tf
│   ├── providers.tf
│   └── versions.tf
├── training/               # Python ML
├── inference/              # Inference handler
├── registry/               # Schema docs
├── ci/                     # GitHub Actions (See docs/cicd.md)
└── docs/                   # Architecture (docs/architecture.md) & Decisions (docs/decisions.md)
```
