
from pathlib import Path
from threading import Lock
import io
import math
import os
import tempfile
import secrets
from fastapi import Depends, Header

import joblib
import pandas as pd

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)
from sklearn.base import clone


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
# Retraining authentication
# --------------------------------------------------

def verify_retrain_key(
    x_api_key: str | None = Header(default=None),
):
    expected_key = os.environ.get("RETRAIN_API_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="Retraining authentication is not configured.",
        )

    if not x_api_key or not secrets.compare_digest(
        x_api_key,
        expected_key,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing retraining API key.",
        )
# --------------------------------------------------
# 2. Supported categorical values
# --------------------------------------------------

COUNTRY_CODES = {
    "AGO", "BDI", "BEN", "BFA", "BWA",
    "CAF", "CIV", "CMR", "COD", "COG",
    "COM", "CPV", "DJI", "DZA", "EGY",
    "ERI", "ETH", "GAB", "GHA", "GIN",
    "GMB", "GNB", "GNQ", "KEN", "LBR",
    "LSO", "MAR", "MDG", "MLI", "MOZ",
    "MRT", "MUS", "MWI", "NAM", "NER",
    "NGA", "RWA", "SEN", "SLE", "STP",
    "SWZ", "SYC", "TCD", "TGO", "TUN",
    "TZA", "UGA", "ZAF", "ZMB", "ZWE",
}

REGIONS = {
    "Middle East & North Africa",
    "Sub-Saharan Africa",
}

INCOME_GROUPS = {
    "High income: nonOECD",
    "Low income",
    "Lower middle income",
    "Upper middle income",
}


# --------------------------------------------------
# 3. Prediction input schema
# --------------------------------------------------

class PredictionInput(BaseModel):

    model_config = ConfigDict(extra="forbid")

    year: StrictInt = Field(ge=1970, le=2016)

    # Population estimates can contain decimals.
    population: StrictFloat = Field(gt=0)

    population_growth: StrictFloat = Field(ge=-10, le=10)

    secondary_enrollment: StrictFloat = Field(ge=0, le=200)

    pupil_teacher_ratio: StrictFloat = Field(gt=0)

    gdp_per_capita: StrictFloat = Field(gt=0)

    primary_education_duration: StrictInt = Field(ge=4, le=7)

    population_age_0_14: StrictFloat = Field(ge=0, le=100)

    country_code: StrictStr
    region: StrictStr
    income_group: StrictStr

    @field_validator(
        "country_code",
        "region",
        "income_group",
    )
    @classmethod
    def validate_categories(cls, value, info):

        allowed = {
            "country_code": COUNTRY_CODES,
            "region": REGIONS,
            "income_group": INCOME_GROUPS,
        }

        if value not in allowed[info.field_name]:
            raise ValueError(
                f"Unsupported {info.field_name}: {value}"
            )

        return value


# --------------------------------------------------
# 4. File paths and saved model
# --------------------------------------------------

API_DIR = Path(__file__).resolve().parent

MODEL_PATH = API_DIR / "best_model.pkl"

TRAINING_DATA_PATH = API_DIR / "training_data.csv"

TARGET_COLUMN = "primary_enrollment"

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

INTEGER_COLUMNS = [
    "year",
    "primary_education_duration",
]

FLOAT_COLUMNS = [
    "population",
    "population_growth",
    "secondary_enrollment",
    "pupil_teacher_ratio",
    "gdp_per_capita",
    "population_age_0_14",
]

model = joblib.load(MODEL_PATH)

model_lock = Lock()


# --------------------------------------------------
# 5. Prediction endpoint
# --------------------------------------------------

@app.post("/predict")
def predict_enrollment(data: PredictionInput):

    with model_lock:
        current_model = model

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
# 6. Validate uploaded CSV
# --------------------------------------------------

def validate_training_csv(
    uploaded_data: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:

    required_columns = feature_columns + [TARGET_COLUMN]

    if (
        len(uploaded_data.columns) != len(required_columns)
        or set(uploaded_data.columns) != set(required_columns)
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "CSV must contain exactly these columns: "
                f"{required_columns}"
            ),
        )

    if uploaded_data.empty:
        raise HTTPException(
            status_code=422,
            detail="The uploaded CSV contains no records.",
        )

    data = uploaded_data[required_columns].copy()

    if data.isnull().any().any():
        raise HTTPException(
            status_code=422,
            detail="CSV contains missing values.",
        )

    # Convert numeric columns
    for column in INTEGER_COLUMNS + FLOAT_COLUMNS + [TARGET_COLUMN]:

        try:
            data[column] = pd.to_numeric(
                data[column],
                errors="raise",
            )

        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422,
                detail=f"{column} must contain numeric values.",
            )

        # Reject infinity, negative infinity and NaN
        if not data[column].map(
            lambda value: math.isfinite(float(value))
        ).all():
            raise HTTPException(
                status_code=422,
                detail=f"{column} contains non-finite values.",
            )

    # Validate integer-valued columns
    for column in INTEGER_COLUMNS:

        if not data[column].map(
            lambda value: float(value).is_integer()
        ).all():
            raise HTTPException(
                status_code=422,
                detail=f"{column} must contain whole numbers.",
            )

        try:
            data[column] = data[column].astype("int64")

        except (ValueError, OverflowError):
            raise HTTPException(
                status_code=422,
                detail=f"{column} contains an invalid integer.",
            )

    # Validate all feature values
    for row_number, record in enumerate(
        data[feature_columns].to_dict(orient="records"),
        start=2,
    ):

        for column in INTEGER_COLUMNS:
            record[column] = int(record[column])

        for column in FLOAT_COLUMNS:
            record[column] = float(record[column])

        try:
            PredictionInput.model_validate(record)

        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid training record at CSV row "
                    f"{row_number}: {exc}"
                ),
            )

    # Gross enrollment can exceed 100%, but cannot be negative
    if (data[TARGET_COLUMN] < 0).any():
        raise HTTPException(
            status_code=422,
            detail="Primary enrollment cannot be negative.",
        )

    return data


# --------------------------------------------------
# 7. Retraining endpoint
# --------------------------------------------------

@app.post("/retrain")
async def retrain_model(
    file: UploadFile = File(...),
    _: None = Depends(verify_retrain_key),
):

    global model

    # Check file extension
    if (
        not file.filename
        or not file.filename.lower().endswith(".csv")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    # Read a bounded amount of data
    try:
        contents = await file.read(MAX_UPLOAD_BYTES + 1)

    finally:
        await file.close()

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="CSV exceeds the 5 MB upload limit.",
        )

    # Parse CSV
    try:
        uploaded_data = pd.read_csv(
            io.BytesIO(contents)
        )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to read the uploaded CSV.",
        )

    # Prevent concurrent model replacements
    if not model_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Another model operation is in progress.",
        )

    temp_path = None

    try:
        feature_columns = list(model.feature_names_in_)

        # Validate uploaded records
        new_data = validate_training_csv(
            uploaded_data,
            feature_columns,
        )

        # Load original training records
        original_data = pd.read_csv(
            TRAINING_DATA_PATH
        )

        required_columns = feature_columns + [TARGET_COLUMN]

        original_data = original_data[required_columns]

        # Combine original training data with new records
        combined_data = pd.concat(
            [original_data, new_data],
            ignore_index=True,
        )

        X = combined_data[feature_columns]
        y = combined_data[TARGET_COLUMN]

        # Clone entire preprocessing + model pipeline
        updated_model = clone(model)

        # Random Forest retraining uses fit(), not partial_fit()
        updated_model.fit(X, y)

        # Save model to a temporary file
        with tempfile.NamedTemporaryFile(
            suffix=".pkl",
            dir=MODEL_PATH.parent,
            delete=False,
        ) as temporary_file:
            temp_path = Path(temporary_file.name)

        joblib.dump(
            updated_model,
            temp_path,
        )

        # Replace the saved model after successful fitting
        os.replace(
            temp_path,
            MODEL_PATH,
        )

        # Activate updated model
        model = updated_model

        return {
            "message": "Model retrained successfully",
            "original_records": len(original_data),
            "new_records": len(new_data),
            "total_training_records": len(combined_data),
            "model_type": type(
                updated_model.named_steps["model"]
            ).__name__,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Model retraining failed.",
        )

    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

        model_lock.release()
