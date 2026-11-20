import sys
import os

api_dir = os.path.join(os.path.dirname(__file__), "summative", "API")
sys.path.insert(0, api_dir)

# Clear any cached modules
for mod in list(sys.modules):
    if mod in ("app_state", "prediction", "retrain"):
        del sys.modules[mod]

print("Importing prediction (which should trigger retrain import)...")
import prediction

print("Routes:")
for r in prediction.app.routes:
    if hasattr(r, 'path'):
        print(f"  {r.path}")

routes = [r.path for r in prediction.app.routes if hasattr(r, 'path')]
print(f"\n/predict count: {routes.count('/predict')}")
print(f"/retrain count: {routes.count('/retrain')}")
