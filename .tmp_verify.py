import sys
import os

# Ensure API dir is on path
api_dir = os.path.join(os.path.dirname(__file__), "summative", "API")
sys.path.insert(0, api_dir)

# Check all three modules import without errors
print("1. Importing app_state...")
import app_state
print("   OK - model loaded:", type(app_state.model).__name__)

print("2. Importing prediction...")
import prediction
print("   OK")

print("3. Importing retrain...")
import retrain
print("   OK - router:", retrain.router)

# Check route registration
routes = sorted(r.path for r in prediction.app.routes if hasattr(r, 'path'))
print("\n4. Routes:", routes)
print("   /predict count:", routes.count("/predict"))
print("   /retrain count:", routes.count("/retrain"))

# Verify no circular imports by checking module loading order
print("\n5. Module check:")
print("   app_state in sys.modules:", "app_state" in sys.modules)
print("   prediction in sys.modules:", "prediction" in sys.modules)
print("   retrain in sys.modules:", "retrain" in sys.modules)

assert routes.count("/predict") == 1, "FAIL: /predict not exactly once"
assert routes.count("/retrain") == 1, "FAIL: /retrain not exactly once"
print("\nALL CHECKS PASSED")
