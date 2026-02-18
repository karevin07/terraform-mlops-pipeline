import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import onnx
import os

# Create dummy data
X = [[0.1, 0.2, 0.3, 0.4]] * 10
y = [100.0] * 10

print("Training model...")
model = RandomForestRegressor(n_estimators=10)
model.fit(X, y)

print("Converting to ONNX...")
initial_type = [('float_input', FloatTensorType([None, 4]))]
onx = convert_sklearn(model, initial_types=initial_type, target_opset=19)

output_path = "model.onnx"
with open(output_path, "wb") as f:
    f.write(onx.SerializeToString())

print(f"Model saved to {output_path}")

# Verify correctness with Python runtime (optional, for comparison)
import onnxruntime as rt
import numpy as np

sess = rt.InferenceSession(output_path)
input_name = sess.get_inputs()[0].name
label_name = sess.get_outputs()[0].name
pred_onx = sess.run([label_name], {input_name: np.array([[0.1, 0.2, 0.3, 0.4]], dtype=np.float32)})[0]
print(f"Python ONNX Prediction: {pred_onx[0][0]}")

