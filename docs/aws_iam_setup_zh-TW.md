# AWS IAM 設定與權限說明

本文件說明如何為 `terraform-mlops-pipeline` 專案設定 AWS IAM 使用者 (User) 及所需的權限。

由於您目前只有 Root 帳號，為了安全起見，建議使用 **IAM Identity Center (推薦)** 或建立專用的 **IAM User** 來管理權限。

## 1. 為什麼需要非 Root 帳號？
*   **安全性**：Root 帳號擁有無限權限，若外洩後果嚴重。
*   **最佳實踐**：AWS 建議日常操作不使用 Root 帳號。

## 2. 專案所需的 AWS 權限

本專案包含兩個主要部分，分別需要不同的權限：

### A. 基礎設施部署 (Terraform)
Terraform 需要建立和管理多種 AWS 資源。建議賦予 **AdministratorAccess** (最簡單且適合個人專案)，或至少包含以下服務的完整存取權限：

*   **S3**: 建立儲存桶 (Bucket) 用於存放資料、模型和 Terraform State (若有設定)。
*   **DynamoDB**: 建立資料表用於儲存模型後設資料 (Metadata)。
*   **ECR (Elastic Container Registry)**: 建立 Docker 映像檔儲存庫。
*   **Lambda**: 建立和更新伺服器無主應用程式。
*   **API Gateway**: 建立 API 用於推論服務。
*   **IAM**: 建立角色 (Role) 供 Lambda 和 API Gateway 執行時使用。
*   **CloudWatch**: 設定 Log Group 和監控。
*   **Budgets**: 設定預算告警。

### B. 應用程式執行 (Python Scripts)
若您在本地執行 `scripts/fetch_stock_data.py`，該腳本需要：
*   **S3**: `PutObject` (上傳 `data.csv`)

---

## 3. [推薦] 使用 IAM User (Access Key)

由於 IAM Identity Center 需要 AWS Organizations 支援 (在某些區域或舊帳號可能需付費或設定複雜)，對於個人專案，使用 **IAM User** 搭配 **Access Key** 是最直接的方式。

> **⚠️ 安全提醒**：Access Key 是長期憑證，請務必妥善保管，**切勿**將其提交到 Git 儲存庫 (`.csv` 檔案應加入 `.gitignore`)。

### 步驟 1：建立 IAM User

1.  登入 [AWS Management Console](https://console.aws.amazon.com/) (使用 Root 帳號)。
2.  搜尋並進入 **IAM** 服務。
3.  點選左側 **Users** -> **Create user**。
4.  **User details**:
    *   User name: 例如 `terraform-admin` 或 `mlops-developer`。
    *   點選 **Next**。
5.  **Permissions**:
    *   選擇 **Attach policies directly**。
    *   搜尋並勾選 **AdministratorAccess** (建議個人開發使用，避免權限不足導致部署失敗)。
    *   *進階選項*：若不希望給予完整管理員權限，請建立自定義 Policy 包含上述服務的 `FullAccess`。
    *   點選 **Next**。
6.  **Review and create**: 確認後點選 **Create user**。

### 步驟 2：取得 Access Key (用於 aws configure)

1.  在使用者列表中，點選剛建立的使用者名稱。
2.  進入 **Security credentials** 頁籤。
3.  往下滑到 **Access keys** 區塊，點選 **Create access key**。
4.  選擇 **Command Line Interface (CLI)**。
5.  勾選確認方塊，點選 **Next** -> **Create access key**。
6.  **複製 Access key ID** 和 **Secret access key** (或下載 `.csv` 檔，並確保它在 `.gitignore` 清單中)。

### 步驟 3：設定本地 AWS CLI

回到終端機，執行以下指令並貼上剛取得的金鑰：

```bash
aws configure
```

依序輸入：
*   `AWS Access Key ID`: [貼上 Access Key ID]
*   `AWS Secret Access Key`: [貼上 Secret Access Key]
*   `Default region name`: `us-east-1` (或您在 Terraform `variables.tf` 中設定的區域)
*   `Default output format`: `json`


---



## 4. 驗證設定

您可以執行以下指令測試權限是否設定成功：

```bash
# 列出 S3 buckets (確認權限)
aws s3 ls

# 確認當前身分
aws sts get-caller-identity
```

此文件完成後，您即可繼續進行 Terraform 部署。
