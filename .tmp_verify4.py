import sys
import os

api_dir = os.path.join(os.path.dirname(__file__), "summative", "API")
sys.path.insert(0, api_dir)

for mod in list(sys.modules):
    if mod in ("app_state", "prediction", "retrain"):
        del sys.modules[mod]

import prediction

# Check all routes including nested
print("All app.routes (raw):")
for r in prediction.app.routes:
    print(f"  type={type(r).__name__} path={getattr(r, 'path', 'N/A')}")

# Try openapi schema
schema = prediction.app.openapi()
paths = list(schema.get("paths", {}).keys())
print(f"\nOpenAPI paths: {paths}")

# Try a TestClient request
from fastapi.testclient import TestClient
client = TestClient(prediction.app)
resp = client.get("/openapi.json")
import json
data = resp.json()
print(f"\nOpenAPI JSON paths: {list(data.get('paths', {}).keys())}")
