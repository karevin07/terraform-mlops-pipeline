# 架構決策紀錄 (ADR)

[English](decisions.md) | [繁體中文](decisions_zh-TW.md)

## 1. 使用 AWS Free Tier (免費層)
**背景**: 需要建立一個具成本效益的 MLOps 流水線，供學習與展示使用。
**決策**: 僅使用符合 AWS Free Tier 資格的服務。嚴格避免使用 ECS Fargate、ALB 與 NAT Gateway。
**後果**: 所有運算皆在 Lambda 上執行；API 路由透過 API Gateway HTTP API 處理。

## 2. 選用 Lambda 而非 ECS Fargate
**背景**: ECS Fargate **沒有 Free Tier**。ALB 也沒有 Free Tier。
**決策**: 使用 Lambda (每月 400,000 GB-秒免費額度) + API Gateway (首年每月 100 萬次免費呼叫)。
**權衡 (Trade-offs)**:
- Lambda 有 15 分鐘超時限制 (硬限制) → 對於小型模型訓練可接受。
- Lambda 有 10GB 記憶體限制 → 足以應付輕量級模型 (如 Scikit-learn)。
- Cold Start 延遲 → 若有需要可透過保溫機制緩解。
**優點**:
- 低流量下 **零成本**。
- 無需管理伺服器 (Serverless)。
- 自動縮減至零 (Scale to zero)。

## 3. 訓練用 Python、推論用 Go（以 ONNX 銜接）
**背景**: 訓練適合留在 Python ML 生態；推論則更需要輕量、低延遲的執行環境，以及語言中立的模型格式。
**決策**:
- **訓練 Lambda**: Python（`scikit-learn`, `pandas`, `skl2onnx`）。
- **推論 Lambda**: Go（`Gin` + ONNX Runtime）。
- **交換格式**: 同時匯出 `model.joblib`（除錯／血緣）與 `model.onnx`（服務用）。推論從 DynamoDB 的 `OnnxUrl` 載入模型。
**後果**:
- 訓練與服務職責分離更清晰。
- 雙語言專案與 Docker build 稍複雜。
- 推論映像檔不必打包沉重的 Python ML 依賴。

## 4. 自建模型註冊表 (DynamoDB + S3)
**背景**: 需要模型版本控制，但不想承擔架設 MLflow Server 或使用 SageMaker Model Registry 的額外成本。
**決策**: 使用 **S3** 儲存模型產物，**DynamoDB** 儲存 Metadata。
**後果**: 簡單、Serverless 且具成本效益。切換版本僅需更新 DynamoDB Metadata（提升 `Status` / 指向另一個 `OnnxUrl`）。

## 5. AWS Budgets 作為成本防線
**背景**: 需要在資源意外產生費用時獲得自動警報。
**決策**: 設定 AWS Budgets 警報，閾值設為 **$0.01**，並發送 Email 通知。
**後果**: 任何超出 Free Tier 的使用量都會立即觸發通知。
