
from pathlib import Path
from threading import Lock

import joblib

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)


# --------------------------------------------------
# 1. Supported categorical values
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
# 2. Prediction input schema
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
# 3. File paths and saved model
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

# --------------------------------------------------
# 4. Shared in-memory model state
# --------------------------------------------------

model = joblib.load(MODEL_PATH)

# Protects reads and replacement of the in-memory model reference.
model_lock = Lock()

# Prevents concurrent retraining operations. Separate from model_lock
# so that fitting a new model does not block prediction requests.
retrain_lock = Lock()


def get_model():
    """Thread-safe read of the current in-memory model."""

    with model_lock:
        return model


def set_model(new_model):
    """Replace the in-memory model reference.

    Caller must already hold ``model_lock``.
    """

    global model
    model = new_model


def get_model_path():
    """Return the model file path.

    Tests override this to redirect writes to a temporary directory.
    """

    return MODEL_PATH


def get_training_data_path():
    """Return the training data file path.

    Tests override this to redirect reads to a temporary copy.
    """

    return TRAINING_DATA_PATH
