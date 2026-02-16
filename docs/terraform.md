# Terraform Guide

[English](terraform.md) | [繁體中文](terraform_zh-TW.md)

This guide explains how to use Terraform to manage the infrastructure for this project.

## Prerequisites

1.  **Terraform CLI**: [Install Terraform](https://developer.hashicorp.com/terraform/downloads) (v1.0+).
2.  **AWS CLI**: [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and configure credentials.

    ```bash
    aws configure
    ```
    For detailed IAM setup instructions, see [AWS IAM Setup](aws_iam_setup.md).

## 🌍 AWS Region Selection

To maximize Free Tier benefits and ensure service availability, we recommend the following regions:

1.  **`us-east-1` (N. Virginia)**: [Recommended] Default region, lowest cost, usually first to receive new features.
2.  **`ap-northeast-1` (Tokyo)**: Lower latency for Asia, but some services might be slightly more expensive.

**How to change the region:**
Modify the `aws_region` variable in `infra/variables.tf`, or create a `terraform.tfvars` file:

```hcl
aws_region = "ap-northeast-1"
```

## 💰 Free Tier Usage Guide

This project is designed to stay within the AWS Free Tier. Key limits:

*   **DynamoDB**: 25 GB storage (Always Free). We use `PAY_PER_REQUEST` billing to avoid idle costs.
*   **Lambda**: 400,000 GB-seconds of compute time per month (Always Free).
    *   Training: 512MB RAM (approx. 200 hours/month free)
    *   Inference: 128MB RAM (approx. 800 hours/month free)
*   **API Gateway**: 1 million calls/month for HTTP APIs (12 months free).
*   **CloudWatch**: 5GB log ingestion and 5GB storage per month.
    *   **Note**: Log retention is set to 7 days to prevent storage costs from accumulating.
*   **S3**: 5GB standard storage (12 months free).

> **Note**: Free Tier limits are per account. If you have other projects running, verify your total usage.

## 📂 Working Directory

All Terraform configuration files are located in the `infra/` directory.

```bash
cd infra
```

## 🛠️ Common Commands

### 1. Initialize

Initialize the working directory. This downloads the necessary providers and sets up the backend.

```bash
terraform init
```

### 2. Validate

Check if the configuration is syntactically valid.

```bash
terraform validate
```

### 3. Plan

Preview the changes that Terraform will make to your infrastructure.

```bash
terraform plan
```

### 4. Apply

Create or update the infrastructure.

```bash
terraform apply
```

To skip the interactive approval prompt:
```bash
terraform apply -auto-approve
```

### 5. Destroy

Remove all resources created by Terraform. **Use with caution!**

```bash
terraform destroy
```

### 6. Cost Estimation

Use `infracost` to estimate cloud costs for the project.

1.  **Get API Key**: [Register for Infracost](https://www.infracost.io/docs/) and get an API Key.
2.  **Configure API Key**:
    ```bash
    infracost auth login
    ```
3.  **View Cost Breakdown**:
    ```bash
    infracost breakdown --path infra/
    ```

    This will show the estimated monthly cost breakdown.

## 🔧 State Management

By default, this project uses a **local backend** (`terraform.tfstate` file in `infra/`).

*   **Do not commit** `*.tfstate` or `*.tfstate.backup` files to version control (they are ignored by `.gitignore`).
*   For team collaboration, consider updating `main.tf` to use an S3 remote backend.
