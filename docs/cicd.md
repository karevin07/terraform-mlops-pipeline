# CI/CD Pipeline Documentation

[English](cicd.md) | [繁體中文](cicd_zh-TW.md)

This project uses **GitHub Actions** to automate infrastructure deployment (Terraform) and Lambda function updates.

## 🚀 Workflow Overview

The CI/CD pipeline is defined in `.github/workflows/deploy.yml`.

```mermaid
graph TD
    Trigger[Push Git Tag v*] --> CI(GitHub Actions)
    
    subgraph Terraform Job
        CI --> Init[Terraform Init]
        Init --> Validate[Terraform Validate]
        Validate --> Plan[Terraform Plan]
        Plan --> Apply[Terraform Apply]
    end

    subgraph Lambda Job
        Apply -->|Success| Login[Login to ECR]
        Login --> Build[Build Docker Images]
        Build --> Push[Push to ECR]
        Push --> Update[Update Lambda Code]
    end

    style Trigger fill:#f9f,stroke:#333,stroke-width:2px
    style CI fill:#bbf,stroke:#333,stroke-width:2px
```

### Trigger

The workflow is triggered **ONLY** when a git tag starting with `v` is pushed.

```bash
git tag v0.1.0
git push origin v0.1.0
```

### Jobs

1.  **`terraform`**:
    *   Initialize Terraform.
    *   Validate configuration.
    *   Plan changes (`terraform plan`).
    *   Apply changes (`terraform apply -auto-approve`).
2.  **`deploy-lambda`** (Runs after `terraform` success):
    *   Login to Amazon ECR.
    *   Build Docker images for Training and Inference.
    *   Push images to ECR.
    *   Update Lambda functions to use the new images.

## 🔑 Configuration

### GitHub Secrets

You must configure the following secrets in your GitHub repository settings (**Settings** > **Secrets and variables** > **Actions**):

| Secret Name | Description | Example |
| :--- | :--- | :--- |
| `AWS_ACCESS_KEY_ID` | AWS IAM Access Key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM Secret Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |

### Environment Variables

The workflow uses the following environment variables (defined in `.github/workflows/deploy.yml`):

*   `AWS_REGION`: `us-east-1` (Default)
*   `TF_WORKING_DIR`: `infra`

## 📦 Deployment Process

1.  **Commit Changes**: Make sure your code changes are committed.
2.  **Tag Release**: Create a new version tag.
    ```bash
    git tag v0.1.0
    ```
3.  **Push Tag**: Push the tag to GitHub to trigger the workflow.
    ```bash
    git push origin v0.1.0
    ```
4.  **Monitor**: check the **Actions** tab in GitHub to see the deployment progress.
