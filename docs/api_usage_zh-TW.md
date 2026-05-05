# Inference API 使用說明

本文件說明如何使用已部署的 Inference API 進行股價預測。

## 1. 取得 API URL

部署完成後，你可以透過 Terraform output 取得 API Gateway 的網址。

```bash
cd infra && terraform output -raw inference_api_url
# 範例輸出: https://abc123xyz.execute-api.us-east-1.amazonaws.com
```

為了方便後續測試，可以將其設為環境變數：

```bash
export API_URL=$(cd infra && terraform output -raw inference_api_url)
```

## 2. API 規格 (Specification)

### Endpoint
- **Method**: `POST`
- **Path**: `/predict`
- **Content-Type**: `application/json`

### 請求格式 (Request Body)

API 接受一個 JSON 物件，包含 `features` 欄位，其值為一個包含 4 個浮點數的陣列。

```json
{
  "features": [SMA_20, RSI_14, Lag_Close_1, Lag_Volume_1]
}
```

**特徵說明 (依順序):**
1.  **SMA_20**: 20日簡單移動平均線 (Simple Moving Average)。
2.  **RSI_14**: 14日相對強弱指標 (Relative Strength Index)。
3.  **Lag_Close_1**: 前一日收盤價 (Previous Day's Close Price)。
4.  **Lag_Volume_1**: 前一日成交量 (Previous Day's Volume)。

### 回應格式 (Response Body)

API 回傳一個 JSON 物件，包含 `predicted_price` (預測股價) 與 `model_version` (模型版本) 欄位。

```json
{
  "predicted_price": 75.50349,
  "model_version": "v20260218021921"
}
```

## 3. 使用範例 (Examples)

### 使用 Makefile (推薦)

專案已內建 `make predict-lambda` 指令，會自動抓取 API URL 並發送測試請求。

```bash
make predict-lambda
```

### 使用 cURL

```bash
curl -X POST "$API_URL/predict" \
     -H "Content-Type: application/json" \
     -d '{"features": [150.5, 65.2, 148.0, 5000000.0]}'
```

### 使用 Python (requests)

```python
import requests
import json

# 設定 API URL
api_url = "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/predict"

# 準備測試資料 (範例)
# [SMA_20, RSI_14, Lag_Close_1, Lag_Volume_1]
payload = {
    "features": [150.5, 65.2, 148.0, 5000000.0]
}

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(api_url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"預測成功: {result}")
        print(f"預測股價: {result['predicted_price']}")
    else:
        print(f"API 錯誤 ({response.status_code}): {response.text}")
        
except Exception as e:
    print(f"連線失敗: {e}")
```

## 4. 常見問題 (FAQ)

### Q: 為什麼收到 503 `Service unavailable`?
**A**: 這表示目前沒有可用的穩定模型 (Stable Model)。請確認訓練工作是否已完成且模型已註冊為 stable 狀態。

### Q: 為什麼收到 404 `Not Found`?
**A**: 請確認 URL 是否正確 (包含 `/predict`)。若 URL 正確仍發生此錯誤，可能是 API Gateway Configuring 問題。
