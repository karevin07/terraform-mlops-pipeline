# CI/CD 流水線說明

[English](cicd.md) | [繁體中文](cicd_zh-TW.md)

本專案使用 **GitHub Actions** 來自動化基礎設施部署 (Terraform) 和 Lambda 函數更新。

## 🚀 工作流程概覽

CI/CD 流水線定義於 `.github/workflows/deploy.yml`。

```mermaid
graph TD
    Trigger[推送 Git Tag v*] --> CI(GitHub Actions)
    
    subgraph Terraform Job
        CI --> Init[Terraform Init]
        Init --> Validate[Terraform Validate]
        Validate --> Plan[Terraform Plan]
        Plan --> Apply[Terraform Apply]
    end

    subgraph Lambda Job
        Apply -->|成功| Login[登入 Amazon ECR]
        Login --> Build[建立 Docker 映像檔]
        Build --> Push[推送至 ECR]
        Push --> Update[更新 Lambda 程式碼]
    end

    style Trigger fill:#f9f,stroke:#333,stroke-width:2px
    style CI fill:#bbf,stroke:#333,stroke-width:2px
```

### 觸發條件

此流程**僅在**推送以 `v` 開頭的 git 標籤 (Tag) 時觸發。

```bash
git tag v0.1.0
git push origin v0.1.0
```

### 作業流程 (Jobs)

1.  **`terraform`**:
    *   初始化 Terraform。
    *   驗證配置 (`terraform validate`)。
    *   規劃變更 (`terraform plan`)。
    *   套用變更 (`terraform apply -auto-approve`)。
2.  **`deploy-lambda`** (在 `terraform` 成功後執行):
    *   登入 Amazon ECR。
    *   建置訓練 (Training) 與推論 (Inference) 的 Docker 映像檔。
    *   推送映像檔至 ECR。
    *   更新 Lambda 函數以使用新的映像檔。

## 🔑 設定

### GitHub Secrets

您必須在 GitHub 儲存庫設定中 (**Settings** > **Secrets and variables** > **Actions**) 配置以下 Secrets：

| Secret 名稱 | 描述 | 範例 |
| :--- | :--- | :--- |
| `AWS_ACCESS_KEY_ID` | AWS IAM Access Key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM Secret Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |

### 環境變數

此流程使用以下環境變數 (定義於 `.github/workflows/deploy.yml` 中):

*   `AWS_REGION`: `us-east-1` (預設)
*   `TF_WORKING_DIR`: `infra`

## 📦 部署流程

1.  **提交變更**: 確保您的程式碼更動已提交 (Commit)。
2.  **標記版本**: 建立一個新版本標籤。
    ```bash
    git tag v0.1.0
    ```
3.  **推送到 GitHub**: 推送標籤以觸發工作流程。
    ```bash
    git push origin v0.1.0
    ```
4.  **監控**: 在 GitHub 的 **Actions** 分頁中查看部署進度。
