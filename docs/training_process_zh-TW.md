# 模型訓練流程 (Model Training Process)

本文檔說明從數據獲取到模型訓練的完整流程。我們使用 `uv` 進行依賴管理，並透過 AWS Lambda 執行訓練工作。

## 1. 數據獲取 (Data Ingestion)

負責從 Yahoo Finance 抓取歷史股價數據並上傳至 S3。

- **腳本**: `scripts/fetch_stock_data.py`
- **主要依賴**: `yfinance`, `boto3`, `pandas`
- **執行流程**:
    1.  指定股票代碼 (Tickers)，例如 `2330.TW`, `0050.TW`, `QQQ`, `SCHD`。
    2.  下載過去 N 天 (預設 365 天) 的歷史數據。
    3.  處理 MultiIndex 資料結構，將其攤平為標準 CSV 格式。
    4.  將合併後的數據 (`Ticker`, `Date`, `Open`, `High`, `Low`, `Close`, `Volume`) 上傳至 S3 Raw Bucket。

**本地執行範例**:
```bash
# 抓取台積電與 0050 的數據 (需先在 .env 設定 S3_RAW_BUCKET)
make fetch-data
```
> **自動化提示**: 執行 `make fetch-data` 上傳檔案後，AWS S3 會自動觸發 Lambda 進行訓練 (Event-Driven)。您可以到 AWS Console 查看 CloudWatch Logs 確認。

## 2. 特徵工程 (Feature Engineering)

在訓練前對原始數據進行處理，生成用於預測的特徵。

- **位置**: `training/train.py` (`feature_engineering` 函數)
- **主要依賴**: `pandas`, `ta` (Technical Analysis library)
- **生成特徵**:
    1.  **移動平均線 (SMA)**: 20日均線 (`SMA_20`)。
    2.  **相對強弱指標 (RSI)**: 14日 RSI (`RSI_14`)。
    3.  **滯後特徵 (Lag Features)**:
        -   `Lag_Close_1`: 前一日收盤價。
        -   `Lag_Volume_1`: 前一日成交量。
- **目標變數 (Target)**:
    -   `Target`: 下一日的收盤價 (`Close.shift(-1)`)。

## 3. 模型訓練 (Model Training)

使用隨機森林回歸模型進行訓練。

- **腳本**: `training/train.py`
- **演算法**: `RandomForestRegressor` (scikit-learn)
    -   `n_estimators`: 100
    -   `max_depth`: 10
- **數據分割**:
    -   按時間序列分割，後 20% 為測試集 (Test Set)，前 80% 為訓練集 (Train Set)。
    -   `shuffle=False` 以防止未來的數據洩漏到訓練集中。
- **評估指標**:
    -   **RMSE** (Root Mean Squared Error)
    -   **MAE** (Mean Absolute Error)
- **產出物 (Artifacts)**:
    -   模型檔案: `model.joblib`
    -   ONNX 模型 (推論用): `model.onnx`
    -   儲存位置: `s3://<model-bucket>/stock-prediction/<version>/model.joblib`

## 4. 模型註冊 (Model Registry)

訓練完成後，將模型元數據 (Metadata) 寫入 DynamoDB。

- **資料表**: `DYNAMODB_TABLE`
- **記錄內容**:
    -   `ModelName`: "stock-prediction"
    -   `Version`: 時間戳記 (例如 `v20231027120000`)
    -   `Metrics`: 訓練指標 (RMSE, MAE)
    -   `ArtifactUrl`: S3 路徑 (Joblib)
    -   `OnnxUrl`: S3 路徑 (ONNX)
    -   `CreatedAt`: 訓練時間

## 5. 本地開發與測試 (Local Development)

使用 `uv` 在本地模擬訓練流程。

### 前置需求
確保已安裝 `uv` 並設定 AWS 憑證 (或使用 mock)。

### 執行訓練測試
我們提供了一個測試腳本來模擬 Lambda 環境：

```bash
# 自動生成假數據並執行測試
make test-local-training
```

## 6. 驗證與成果 (Verification)

當您執行 `make fetch-data` 觸發訓練後，可以透過以下 `make` 指令快速驗證成果：

### 6.1 檢查 CloudWatch Logs (確認訓練執行)
查看最近 1 小時的 Training Lambda 執行日誌：

```bash
make logs-training
```

### 6.2 檢查 S3 Model Artifacts (確認模型產出)
列出 S3 Bucket 中的模型檔案：

```bash
make check-model
```

### 6.3 檢查 DynamoDB Metadata (確認註冊資訊)
查詢 DynamoDB 中的模型註冊紀錄：

```bash
make check-metadata
```
