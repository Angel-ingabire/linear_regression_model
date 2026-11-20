
import io
import math
import os
import tempfile
import secrets
from pathlib import Path

import joblib
import pandas as pd
from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    UploadFile,
)
from sklearn.base import clone

from app_state import (
    FLOAT_COLUMNS,
    INTEGER_COLUMNS,
    MAX_UPLOAD_BYTES,
    PredictionInput,
    TARGET_COLUMN,
    get_model,
    get_model_path,
    get_training_data_path,
    retrain_lock,
    set_model,
)


router = APIRouter()


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
# Validate uploaded CSV
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
# Retraining endpoint
# --------------------------------------------------

@router.post("/retrain")
async def retrain_model(
    file: UploadFile = File(...),
    _: None = Depends(verify_retrain_key),
):

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

    # Prevent concurrent retraining operations
    if not retrain_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Another model operation is in progress.",
        )

    temp_path = None

    try:
        # Briefly acquire model_lock to read the current model,
        # then release it before the long-running fit so that
        # prediction requests are not blocked during training.
        current_model = get_model()

        feature_columns = list(current_model.feature_names_in_)

        # Validate uploaded records
        new_data = validate_training_csv(
            uploaded_data,
            feature_columns,
        )

        # Load original training records
        original_data = pd.read_csv(
            get_training_data_path()
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
        updated_model = clone(current_model)

        # Random Forest retraining uses fit(), not partial_fit()
        updated_model.fit(X, y)

        # Save model to a temporary file
        model_path = get_model_path()

        with tempfile.NamedTemporaryFile(
            suffix=".pkl",
            dir=model_path.parent,
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
            model_path,
        )

        # Safely replace the in-memory model reference. ``set_model``
        # acquires ``model_lock`` itself and holds it only for the
        # assignment, so prediction requests pause for microseconds.
        set_model(updated_model)

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

        retrain_lock.release()
