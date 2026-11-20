
import pandas as pd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app_state import PredictionInput, get_model
from retrain import router as retrain_router


# --------------------------------------------------
# 1. Initialize FastAPI
# --------------------------------------------------

app = FastAPI(
    title="African Primary School Enrollment Prediction API",
    description=(
        "Predicts gross primary school enrollment rates "
        "using a trained Random Forest regression model."
    ),
    version="1.0.0",
)

# --------------------------------------------------
# CORS configuration
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


# --------------------------------------------------
# 2. Prediction endpoint
# --------------------------------------------------

@app.post("/predict")
def predict_enrollment(data: PredictionInput):

    current_model = get_model()

    feature_columns = list(current_model.feature_names_in_)

    input_data = data.model_dump()

    input_df = pd.DataFrame(
        [input_data],
        columns=feature_columns,
    )

    try:
        prediction = current_model.predict(input_df)[0]

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Prediction failed."
        )

    return {
        "predicted_primary_enrollment": float(prediction)
    }


# --------------------------------------------------
# 3. Register the retraining router
# --------------------------------------------------
# Import graph: prediction -> retrain -> app_state.
# retrain.py never imports prediction.py, and both endpoint modules
# take their shared state from app_state.py, so there is no cycle.

app.include_router(retrain_router)
