# 推論服務部署指南 (AWS Free Tier)

本指南說明如何將 Go + ONNX 推論服務部署至 AWS，並確保符合 **AWS Free Tier** (免費方案) 的限制。

## 1. 架構與成本分析 (Architecture & Cost)

採用的架構經過優化，以最小化成本並符合免費方案資格：

*   **運算 (AWS Lambda)**:
    *   **配置**: 256MB 記憶體, 30秒逾時。
    *   **Free Tier**: 每月 400,000 GB-seconds。以 256MB (0.25GB) 計算，相當於 **1,600,000 秒** (約 444 小時) 的執行時間。
    *   **優勢**: Serverless 架構，無請求時不計費 (Scale to Zero)。
*   **API (Amazon API Gateway)**:
    *   **類型**: HTTP API (比 REST API 更輕量、低延遲)。
    *   **Payload Format**: 必須設定為 **1.0** (因 `aws-lambda-go-api-proxy` 預設支援 v1.0)。
    *   **Free Tier**: HTTP API 每月前 100 萬次請求免費 (首 12 個月)。
    *   **成本**: 超過後每百萬次請求僅需 $1.00 USD。
*   **儲存 (Amazon ECR)**:
    *   **用途**: 存放 Docker Image。
    *   **Free Tier**: 私有儲存庫每月 500MB 免費 (首 12 個月)。
    *   **策略**: 建議定期清理舊的 Image Tag 以避免超過 500MB。

## 2. 部署流程 (Deployment Workflow)

請確保已安裝 `docker`, `aws-cli`, `terraform`。

### 步驟 1: 建置並推送 Docker Image

使用 Makefile 指令自動登入 ECR、建置 Image 並推送到 AWS 私有儲存庫。

```bash
# 1. 登入 ECR (確保 aws configure 已設定)
make ecr-login

# 2. 建置並推送推論服務 Image
make push-inference

# 或一次推送所有 Images (包含訓練)
make deploy-images
```

### 步驟 2: 部署基礎設施 (Infrastructure)

使用 Terraform 部署或更新 AWS 資源 (Lambda, API Gateway, IAM 等)。

```bash
# 初始化 (只需執行一次)
make tf-init

# 檢視變更計畫
make tf-plan

# 套用變更
make tf-apply
```

### 步驟 3: 驗證部署 (Verification)

部署完成後，Terraform 會輸出 API Gateway 的 URL。

1.  **取得 API URL**:
    ```bash
    cd infra && terraform output -raw inference_api_url
    # 輸出範例: https://xyz123.execute-api.us-east-1.amazonaws.com
    ```

2.  **測試推論**:
    使用 `curl` 發送測試請求 (請替換 `<API_URL>`)：

    ```bash
    curl -X POST <API_URL>/predict \
         -H "Content-Type: application/json" \
         -d '{"features": [0.1, 0.2, 0.3, 0.4]}'
    ```

    預期回應：
    ```json
    {"prediction": [123.45]}
    ```

## 3. 更新服務 (Update Service)

若只更新了程式碼 (Go) 或模型 (ONNX)，不需重新執行 Terraform，只需更新 Lambda 函數即可。

```bash
# 1. 重建並推送新 Image
make push-inference

# 2. 強制 Lambda 更新 (使用 Makefile)
# 此指令會自動查詢 Terraform output 與 ECR URI，並更新 Lambda 函數程式碼
make deploy-inference-lambda
```

## 4. 監控與除錯 (Monitoring)

-   **CloudWatch Logs**: 查看 Lambda 執行日誌。
    ```bash
    # 需安裝 aws-cli v2
    aws logs tail /aws/lambda/$(cd infra && terraform output -raw inference_function_name) --follow
    ```

### 常見錯誤排除 (Troubleshooting)

#### 1. 404 `{"message":"Not Found"}`
*   **原因**: API Gateway 的 Payload Format Version 設定為 `2.0`，但 Lambda 程式碼預期的是 `1.0` 格式。
*   **解法**: 檢查 Terraform `aws_apigatewayv2_integration` 設定，確保 `payload_format_version = "1.0"`。

#### 2. 503 `{"error": "Service unavailable"}`
*   **原因**: Lambda 找不到可用的 ONNX 模型。通常發生在初次部署後，尚未執行訓練，或者 DynamoDB 中缺乏 `stable` 狀態的模型記錄。
*   **解法**:
    1.  檢查 DynamoDB 是否有 `Status=stable` 且包含 `OnnxUrl` 的記錄。
    2.  若無，請手動觸發訓練 (`make test-local-training` 或 AWS Console) 並確認訓練成功生成 ONNX 模型。
    3.  確認 DynamoDB 記錄已更新為 `stable`。
