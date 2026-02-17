# Terraform 使用指南

[English](terraform.md) | [繁體中文](terraform_zh-TW.md)

本指南說明如何使用 Terraform 來管理此專案的基礎設施。

## 前置需求

1.  **Terraform CLI**: [安裝 Terraform](https://developer.hashicorp.com/terraform/downloads) (v1.0+)。
2.  **AWS CLI**: [安裝 AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) 並設定憑證。
  3.  **AWS IAM 設定**: 請參考 [AWS IAM 設定與權限說明](aws_iam_setup_zh-TW.md) 完成使用者建立與 `aws configure` 設定。

    ```bash
    # 或者舊式 Access Key
    aws configure
    ```

    ```

## 🌍 AWS Region 選擇與 Free Tier 建議

### 推薦 Region
本專案預設使用 **`us-east-1` (N. Virginia)**。
*   **優點**：功能最完整、價格通常最低、也是大部分教學的預設值。
*   **延遲**：若您在台灣，連線延遲約 200ms，但對於此 MLOps 專案的「批次訓練」與「非即時推論」影響極小。
*   **替代方案**：若非常介意延遲，可改用 **`ap-northeast-1` (Tokyo)**，但需注意部分服務定價可能只有些微差異。

### 更改 Region
若您希望更改部署區域，請在 `infra/` 目錄下建立一個 `terraform.tfvars` 檔案：

```hcl
# infra/terraform.tfvars
aws_region = "ap-northeast-1"
```

### 💰 AWS Free Tier 注意事項
本專案的 Terraform 配置已針對 Free Tier 進行優化，但請務必留意以下限制 (以 AWS 官方最新公告為準)：

*   **DynamoDB**: 設定為 `PAY_PER_REQUEST` (On-Demand)。
    *   每月 25 GB 儲存免費。
    *   每月 25 個 WCU 和 25 個 RCU 免費。
*   **Lambda**:
    *   每月 400,000 GB-seconds 免費運算時間。
    *   每月 1,000,000 次免費請求。
    *   *注意*：訓練任務 (Training) 設定記憶體為 512MB，若執行過久會消耗較多 GB-seconds。
*   **API Gateway (HTTP API)**:
    *   前 12 個月每月 100 萬次呼叫免費。
*   **S3**:
    *   標準儲存 5GB 免費。
    *   20,000 個 GET Request / 2,000 個 PUT Request 免費。
*   **CloudWatch**:
    *   Logs 保留設定為 7 天以節省儲存空間。
- **S3 Event Notification**: 設定 Raw Data Bucket 自動觸發 Training Lambda (Event-Driven 架構)。

> **💡 建議**：定期檢查 AWS Billing Dashboard，並設定 Budgets 告警 (本專案已包含 Budgets 模組) 以避免意外費用。

## 📂 工作目錄

所有的 Terraform 設定檔皆位於 `infra/` 目錄中。

```bash
cd infra
```

## 🛠️ 常用指令

### 1. 初始化 (Initialize)

初始化工作目錄。此步驟會下載必要的 Providers 並設定 Backend。

```bash
make tf-init
```

### 2. 驗證 (Validate)

檢查設定檔的語法是否正確。

```bash
cd infra && terraform validate
```

### 3. 規劃 (Plan)

預覽 Terraform 將對基礎設施進行的變更。

```bash
make tf-plan
```

### 3.5. [重要] 建置並推送 Docker Image

Terraform 會建立 ECR Repository，但**不會**自動建置和推送 Docker Image。因此在第一次 `terraform apply` 建立 Lambda 之前，您必須手動推送 Image，否則會出現 `InvalidParameterValueException: Source image does not exist` 錯誤。

我們已提供 `Makefile` 自動化此與流程。

1.  **設定環境變數**:
    複製 `.env.example` 到 `.env` 並填入您的 AWS Account ID：
    ```bash
    cp .env.example .env
    # 編輯 .env 填入 AWS_ACCOUNT_ID
    ```

2.  **執行部署指令**:
    此指令會自動登入 ECR、建置 Image 並推送到 Repository。
    ```bash
    make deploy-images
    ```

### 4. 套用 (Apply)

建立或更新基礎設施。

```bash
make tf-apply
```

### 5. 銷毀 (Destroy)

移除所有由 Terraform 建立的資源。**請謹慎使用！**

```bash
make tf-destroy
```

### 6. 成本估算 (Cost Estimation)

使用 `infracost` 來預估專案的雲端費用。

1.  **取得 API Key**: [註冊 Infracost](https://www.infracost.io/docs/) 並取得 API Key。
2.  **設定 API Key**:
    ```bash
    infracost auth login
    ```
3.  **查看成本分析**:
    ```bash
    make cost-estimate
    ```

    這將會顯示預估的每月費用明細。

## 🔧 狀態管理 (State Management)

預設情況下，本專案使用 **Local Backend** (在 `infra/` 目錄下的 `terraform.tfstate` 檔案)。

*   **請勿提交** `*.tfstate` 或 `*.tfstate.backup` 檔案至版本控制系統 (它們已被 `.gitignore` 排除)。
*   若需團隊協作，請考慮更新 `main.tf` 以使用 S3 Remote Backend。
