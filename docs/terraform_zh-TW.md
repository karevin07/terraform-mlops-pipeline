# Terraform 使用指南

[English](terraform.md) | [繁體中文](terraform_zh-TW.md)

本指南說明如何使用 Terraform 來管理此專案的基礎設施。

## 前置需求

1.  **Terraform CLI**: [安裝 Terraform](https://developer.hashicorp.com/terraform/downloads) (v1.0+)。
2.  **AWS CLI**: [安裝 AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) 並設定憑證。

    ```bash
    aws configure
    ```

## 📂 工作目錄

所有的 Terraform 設定檔皆位於 `infra/` 目錄中。

```bash
cd infra
```

## 🛠️ 常用指令

### 1. 初始化 (Initialize)

初始化工作目錄。此步驟會下載必要的 Providers 並設定 Backend。

```bash
terraform init
```

### 2. 驗證 (Validate)

檢查設定檔的語法是否正確。

```bash
terraform validate
```

### 3. 規劃 (Plan)

預覽 Terraform 將對基礎設施進行的變更。

```bash
terraform plan
```

### 4. 套用 (Apply)

建立或更新基礎設施。

```bash
terraform apply
```

若要跳過互動式確認提示：
```bash
terraform apply -auto-approve
```

### 5. 銷毀 (Destroy)

移除所有由 Terraform 建立的資源。**請謹慎使用！**

```bash
terraform destroy
```

## 🔧 狀態管理 (State Management)

預設情況下，本專案使用 **Local Backend** (在 `infra/` 目錄下的 `terraform.tfstate` 檔案)。

*   **請勿提交** `*.tfstate` 或 `*.tfstate.backup` 檔案至版本控制系統 (它們已被 `.gitignore` 排除)。
*   若需團隊協作，請考慮更新 `main.tf` 以使用 S3 Remote Backend。
