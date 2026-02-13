# Terraform Guide

[English](terraform.md) | [繁體中文](terraform_zh-TW.md)

This guide explains how to use Terraform to manage the infrastructure for this project.

## Prerequisites

1.  **Terraform CLI**: [Install Terraform](https://developer.hashicorp.com/terraform/downloads) (v1.0+).
2.  **AWS CLI**: [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and configure credentials.

    ```bash
    aws configure
    ```

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

## 🔧 State Management

By default, this project uses a **local backend** (`terraform.tfstate` file in `infra/`).

*   **Do not commit** `*.tfstate` or `*.tfstate.backup` files to version control (they are ignored by `.gitignore`).
*   For team collaboration, consider updating `main.tf` to use an S3 remote backend.
