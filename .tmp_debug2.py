import sys
import os
import traceback

api_dir = os.path.join(os.path.dirname(__file__), "summative", "API")
sys.path.insert(0, api_dir)

os.environ["RETRAIN_API_KEY"] = "test-secret-key"

import prediction
import retrain
import app_state
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Manually test the retrain logic
import io
import pandas as pd

contents = b"year,population\n1,100\n"
uploaded_data = pd.read_csv(io.BytesIO(contents))

# Get model
current_model = app_state.get_model()
feature_columns = list(current_model.feature_names_in_)
print(f"Feature columns: {feature_columns}")

try:
    result = retrain.validate_training_csv(uploaded_data, feature_columns)
    print(f"Result: {result}")
except HTTPException as e:
    print(f"HTTPException raised correctly: {e.status_code} - {e.detail}")
except Exception as e:
    print(f"Other exception: {type(e).__name__}: {e}")
    traceback.print_exc()
