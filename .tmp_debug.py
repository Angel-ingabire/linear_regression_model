import sys
import os

api_dir = os.path.join(os.path.dirname(__file__), "summative", "API")
sys.path.insert(0, api_dir)

os.environ["RETRAIN_API_KEY"] = "test-secret-key"

import prediction
from fastapi.testclient import TestClient

client = TestClient(prediction.app)

# Test invalid CSV columns
resp = client.post(
    "/retrain",
    files={"file": ("bad.csv", b"year,population\n1,100\n", "text/csv")},
    headers={"x-api-key": "test-secret-key"},
)
print(f"Status: {resp.status_code}")
print(f"Body: {resp.json()}")
