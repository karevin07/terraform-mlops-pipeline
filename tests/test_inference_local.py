
import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys
import joblib

sys.path.append(os.getcwd())

class TestStockPredictionInference(unittest.TestCase):

    @patch('inference.app.s3')
    @patch('inference.app.table')
    @patch('inference.app.joblib')
    def test_lambda_handler(self, mock_joblib, mock_table, mock_s3):
        # Import after patching if needed, but patching module globals works on import if they are used at runtime
        from inference.app import lambda_handler
        
        # 1. Mock DynamoDB response for model version
        mock_table.query.return_value = {
            "Items": [
                {
                    "ModelName": "stock-prediction",
                    "Version": "v1",
                    "Status": "stable",
                    "ArtifactUrl": "s3://test-bucket/model.joblib"
                }
            ]
        }
        
        # 2. Mock S3 get object
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"fake-model-bytes")
        }
        
        # 3. Mock joblib load and predict
        mock_model = MagicMock()
        mock_model.predict.return_value = [150.5] # Predicted price
        mock_joblib.load.return_value = mock_model
        
        # 4. Create Event
        event = {
            "body": json.dumps({
                "features": [100.0, 50.0, 101.0, 10000.0] # SMA, RSI, Lag_Close, Lag_Vol
            })
        }
        
        # 5. Run Handler
        response = lambda_handler(event, None)
        
        # 6. Verify
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertIn("predicted_price", body)
        self.assertEqual(body["predicted_price"], 150.5)
        self.assertEqual(body["model_version"], "v1")
        
        print("Inference test clean pass.")

if __name__ == '__main__':
    unittest.main()
