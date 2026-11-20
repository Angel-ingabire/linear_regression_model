
import os
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
# Production defaults point at the files that ship with the API.
#
# The two optional environment variables below let an isolated test
# process redirect the model and training data to temporary copies
# BEFORE this module is imported. Because the paths are resolved at
# import time, the in-memory model is loaded from the redirected file
# and every later write targets that same redirected path - no
# post-import monkeypatching is required or relied upon.
#
# When the variables are unset, behaviour is identical to before.

API_DIR = Path(__file__).resolve().parent

MODEL_PATH_ENV_VAR = "APP_MODEL_PATH"
TRAINING_DATA_PATH_ENV_VAR = "APP_TRAINING_DATA_PATH"

DEFAULT_MODEL_PATH = API_DIR / "best_model.pkl"

DEFAULT_TRAINING_DATA_PATH = API_DIR / "training_data.csv"


def _resolve_path(env_var: str, default_path: Path) -> Path:
    """Return the path configured in ``env_var``, else ``default_path``.

    Called once at import time, before the model is loaded, so that a
    test process can fully redirect this module's file access.
    """

    configured_path = os.environ.get(env_var, "").strip()

    if not configured_path:
        return default_path

    return Path(configured_path).expanduser().resolve()


MODEL_PATH = _resolve_path(
    MODEL_PATH_ENV_VAR,
    DEFAULT_MODEL_PATH,
)

TRAINING_DATA_PATH = _resolve_path(
    TRAINING_DATA_PATH_ENV_VAR,
    DEFAULT_TRAINING_DATA_PATH,
)

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
    """Thread-safe read of the current in-memory model reference.

    ``model_lock`` is held only for the duration of the attribute read,
    so the (potentially slow) use of the returned estimator happens
    without blocking other requests.
    """

    with model_lock:
        return model


def set_model(new_model):
    """Atomically replace the in-memory model reference.

    Acquires ``model_lock`` itself. Callers must NOT already hold it -
    ``threading.Lock`` is not reentrant, so acquiring it twice in the
    same thread would deadlock.
    """

    global model

    with model_lock:
        model = new_model


def get_model_path() -> Path:
    """Return the model file path.

    With no configuration this is ``API_DIR/best_model.pkl``. Tests
    redirect it before import via ``APP_MODEL_PATH``.
    """

    return MODEL_PATH


def get_training_data_path() -> Path:
    """Return the training data file path.

    With no configuration this is ``API_DIR/training_data.csv``. Tests
    redirect it before import via ``APP_TRAINING_DATA_PATH``.
    """

    return TRAINING_DATA_PATH
