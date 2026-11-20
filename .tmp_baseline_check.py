import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "summative", "API"))
import prediction
routes = sorted(r.path for r in prediction.app.routes if hasattr(r, 'path'))
print("Routes:", routes)
print("predict count:", routes.count("/predict"))
print("retrain count:", routes.count("/retrain"))
