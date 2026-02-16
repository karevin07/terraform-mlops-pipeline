# AWS IAM Setup and Permissions Guide

[繁體中文](aws_iam_setup_zh-TW.md) | [English](aws_iam_setup.md)

This document explains how to set up an AWS IAM User and required permissions for the `terraform-mlops-pipeline` project.

Since you are currently using the Root account, for security reasons, it is highly recommended to create a dedicated **IAM User** to manage permissions.

## 1. Why Not Use Root Account?
*   **Security**: Root account has unrestricted access; if compromised, the consequences are severe.
*   **Best Practice**: AWS recommends not using the Root account for daily operations.

## 2. Required AWS Permissions

This project consists of two main parts requiring different permissions:

### A. Infrastructure Deployment (Terraform)
Terraform needs to create and manage various AWS resources. Granting **AdministratorAccess** involves the simplest setup and is suitable for personal projects, or ensuring full access permissions for at least the following services:

*   **S3**: Create Buckets for storing data, models, and Terraform State (if configured).
*   **DynamoDB**: Create tables for storing model metadata.
*   **ECR (Elastic Container Registry)**: Create Docker image repositories.
*   **Lambda**: Create and update serverless applications.
*   **API Gateway**: Create APIs for inference services.
*   **IAM**: Create Roles for Lambda and API Gateway execution.
*   **CloudWatch**: Configure Log Groups and monitoring.
*   **Budgets**: Configure budget alarms.

### B. Application Execution (Python Scripts)
If you run `scripts/fetch_stock_data.py` locally, the script requires:
*   **S3**: `PutObject` (upload `data.csv`)

---

## 3. [Recommended] Use IAM User (Access Key)

Since IAM Identity Center requires AWS Organizations support (which may require paid plans or complex setup in some regions/legacy accounts), using an **IAM User** with **Access Keys** is the most straightforward method for personal projects.

> **⚠️ Security Warning**: Access Keys are long-term credentials. Please keep them secure and **NEVER** commit them to Git repositories (ensure `.csv` files are added to `.gitignore`).

### Step 1: Create IAM User

1.  Log in to the [AWS Management Console](https://console.aws.amazon.com/) (using Root account).
2.  Search for and enter the **IAM** service.
3.  Click **Users** -> **Create user** on the left menu.
4.  **User details**:
    *   User name: e.g., `terraform-admin` or `mlops-developer`.
    *   Click **Next**.
5.  **Permissions**:
    *   Select **Attach policies directly**.
    *   Search for and select **AdministratorAccess** (recommended for personal development to avoid deployment failures due to insufficient permissions).
    *   *Advanced Option*: If you prefer not to grant full admin access, create a custom Policy including `FullAccess` for the services listed above.
    *   Click **Next**.
6.  **Review and create**: Confirm details and click **Create user**.

### Step 2: Retrieve Access Key (for aws configure)

1.  In the user list, click on the newly created user name.
2.  Go to the **Security credentials** tab.
3.  Scroll down to the **Access keys** section and click **Create access key**.
4.  Select **Command Line Interface (CLI)**.
5.  Check the confirmation box and click **Next** -> **Create access key**.
6.  **Copy Access key ID** and **Secret access key** (or download the `.csv` file, ensuring it is in your `.gitignore` list).

### Step 3: Configure Local AWS CLI

Return to your terminal, run the following command, and paste the keys you just obtained:

```bash
aws configure
```

Enter the following as prompted:
*   `AWS Access Key ID`: [Paste Access Key ID]
*   `AWS Secret Access Key`: [Paste Secret Access Key]
*   `Default region name`: `us-east-1` (or the region set in `variables.tf`)
*   `Default output format`: `json`

## 4. Verify Configuration

You can run the following commands to test if permissions are set correctly:

```bash
# List S3 buckets (verify permissions)
aws s3 ls

# Verify current identity
aws sts get-caller-identity
```

Once this document is completed, you can proceed with Terraform deployment.
