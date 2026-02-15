
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from training.train import train_model, load_data, feature_engineering

class TestStockPredictionTraining(unittest.TestCase):
    
    @patch('training.train.s3')
    def test_training_pipeline(self, mock_s3):
        # 1. Setup Mock Data
        try:
            df = pd.read_csv("tests/data.csv")
        except FileNotFoundError:
            self.fail("tests/data.csv not found. Run generate_sample_data.py first.")
            
        # Mock s3.get_object to return the CSV content
        from io import BytesIO
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        mock_s3.get_object.return_value = {
            "Body": csv_buffer
        }
        
        # 2. Test Feature Engineering
        # We can test feature_engineering directly or via main
        # Let's test basic feature engineering
        # Note: train.py might need slight adjustments to be imported cleanly if logic is at top level
        # Assuming we can import functions.
        
        # 3. Test Full Flow (Run main logic effectively)
        # We'll simulate the main block logic here to reuse functions
        
        print("Testing load_data...")
        data = load_data("test-bucket", "data.csv")
        self.assertFalse(data.empty)
        self.assertIn("Close", data.columns)
        
        print("Testing feature_engineering...")
        df_processed = feature_engineering(data)
        self.assertIn("SMA_20", df_processed.columns)
        self.assertIn("RSI_14", df_processed.columns)
        self.assertIn("Target", df_processed.columns)
        
        # 4. TRaining
        print("Testing model training...")
        # Prepare X and y
        features = ["SMA_20", "RSI_14", "Lag_Close_1", "Lag_Volume_1"]
        target = "Target"
        
        X = df_processed[features]
        y = df_processed[target]
        
        # Split
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]
        
        # Train
        # We need to import RandomForestRegressor from train.py if defined or valid
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=10, max_depth=5)
        model.fit(X_train, y_train)
        
        preds = model.predict(X_test)
        self.assertEqual(len(preds), len(y_test))
        print("Training test clean pass.")

if __name__ == '__main__':
    unittest.main()
