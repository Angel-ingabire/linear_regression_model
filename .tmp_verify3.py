import sys
import os

api_dir = os.path.join(os.path.dirname(__file__), "summative", "API")
sys.path.insert(0, api_dir)

for mod in list(sys.modules):
    if mod in ("app_state", "prediction", "retrain"):
        del sys.modules[mod]

import prediction
import retrain

print("retrain module:", retrain)
print("retrain.router:", retrain.router)
print("retrain.router.routes:", retrain.router.routes)
for r in retrain.router.routes:
    if hasattr(r, 'path'):
        print(f"  router route: {r.path} methods={getattr(r, 'methods', None)}")

print("\napp routes after include_router:")
for r in prediction.app.routes:
    if hasattr(r, 'path'):
        print(f"  {r.path}")

print("\nretrain in sys.modules:", "retrain" in sys.modules)
print("_retrain_router in prediction dir:", "_retrain_router" in dir(prediction))
