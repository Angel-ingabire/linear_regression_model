"""Helpers that let the API tests run against isolated file copies.

The API resolves its model and training-data paths once, at import time,
from the ``APP_MODEL_PATH`` and ``APP_TRAINING_DATA_PATH`` environment
variables (see ``app_state.py``). This module configures those variables
*and* is imported before ``app_state``/``prediction``, so the application
under test never holds a reference to the real ``best_model.pkl`` or
``training_data.csv``.

Nothing here is imported by the application itself - it is test support
only. The module name deliberately does not match ``test_*.py`` so that
pytest does not collect it as a test module.
"""

import csv
import hashlib
import io
import os
import shutil
import tempfile
from pathlib import Path

API_DIR = Path(__file__).resolve().parent

# The files that ship with the API. Tests must never write to these.
PRODUCTION_MODEL_PATH = API_DIR / "best_model.pkl"
PRODUCTION_DATA_PATH = API_DIR / "training_data.csv"

# Environment variables consumed by ``app_state``.
MODEL_PATH_ENV_VAR = "APP_MODEL_PATH"
TRAINING_DATA_PATH_ENV_VAR = "APP_TRAINING_DATA_PATH"

# Environment variable consumed by the retraining endpoint.
API_KEY_ENV_VAR = "RETRAIN_API_KEY"
TEST_API_KEY = "test-secret-key"

MODEL_FILENAME = "best_model.pkl"
DATA_FILENAME = "training_data.csv"

# A payload that satisfies every field of ``PredictionInput``.
VALID_PREDICTION_PAYLOAD = {
    "year": 2010,
    "population": 10000000.0,
    "population_growth": 2.5,
    "secondary_enrollment": 40.0,
    "pupil_teacher_ratio": 35.0,
    "gdp_per_capita": 800.0,
    "primary_education_duration": 6,
    "population_age_0_14": 42.0,
    "country_code": "AGO",
    "region": "Sub-Saharan Africa",
    "income_group": "Low income",
}

UPLOAD_LIMIT_BYTES = 5 * 1024 * 1024


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of ``path`` as lowercase hex."""

    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)

    return digest.hexdigest()


def production_hashes() -> dict:
    """Return the hashes of the shipped model and training data."""

    return {
        "model": sha256_file(PRODUCTION_MODEL_PATH),
        "training_data": sha256_file(PRODUCTION_DATA_PATH),
    }


def create_isolated_workspace(prefix: str = "retrain_isolation_") -> Path:
    """Create a temp directory holding copies of the shipped files."""

    workspace = Path(tempfile.mkdtemp(prefix=prefix))

    shutil.copy2(PRODUCTION_MODEL_PATH, workspace / MODEL_FILENAME)
    shutil.copy2(PRODUCTION_DATA_PATH, workspace / DATA_FILENAME)

    return workspace


def configure_environment(workspace: Path) -> tuple:
    """Point ``app_state`` at ``workspace`` via environment variables.

    Must be called BEFORE ``app_state`` is imported for the first time,
    because the module resolves its paths at import.
    """

    model_path = workspace / MODEL_FILENAME
    data_path = workspace / DATA_FILENAME

    os.environ[MODEL_PATH_ENV_VAR] = str(model_path)
    os.environ[TRAINING_DATA_PATH_ENV_VAR] = str(data_path)

    return model_path, data_path


def is_inside(path: Path, directory: Path) -> bool:
    """Return True when ``path`` resolves inside ``directory``."""

    try:
        Path(path).resolve().relative_to(Path(directory).resolve())
    except ValueError:
        return False

    return True


def assert_inside(path: Path, directory: Path) -> None:
    """Fail loudly if ``path`` escapes the isolated ``directory``."""

    if not is_inside(path, directory):
        raise AssertionError(
            f"Refusing to run: {path} is outside the isolated "
            f"workspace {directory}."
        )


def _read_training_rows(row_count: int) -> tuple:
    """Return the header and first ``row_count`` data rows of the data."""

    with open(PRODUCTION_DATA_PATH, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)

        rows = []
        for row in reader:
            rows.append(row)

            if len(rows) == row_count:
                break

    return header, rows


def build_sample_upload_bytes(row_count: int = 5) -> bytes:
    """Build a small, fully valid retraining CSV from the real data."""

    header, rows = _read_training_rows(row_count)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)

    return buffer.getvalue().encode("utf-8")


def build_wrong_columns_upload_bytes() -> bytes:
    """Build a CSV whose header does not match the model's features."""

    return b"year,population\n2010,10000000\n"


def build_non_numeric_upload_bytes() -> bytes:
    """Build a CSV that is shaped correctly but holds a text number."""

    header, rows = _read_training_rows(1)

    population_index = header.index("population")
    rows[0][population_index] = "not-a-number"

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)

    return buffer.getvalue().encode("utf-8")


def build_out_of_range_upload_bytes() -> bytes:
    """Build a CSV whose ``year`` is outside the accepted range."""

    header, rows = _read_training_rows(1)

    year_index = header.index("year")
    rows[0][year_index] = "2099"

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)

    return buffer.getvalue().encode("utf-8")


def build_negative_target_upload_bytes() -> bytes:
    """Build a CSV whose target value is negative."""

    header, rows = _read_training_rows(1)

    target_index = header.index("primary_enrollment")
    rows[0][target_index] = "-1"

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)

    return buffer.getvalue().encode("utf-8")


def build_oversized_upload_bytes() -> bytes:
    """Build a CSV larger than the 5 MB upload limit."""

    sample = build_sample_upload_bytes(row_count=1)

    header, separator, row = sample.partition(b"\n")

    repeated_row = row

    body = bytearray(header + b"\n")

    while len(body) <= UPLOAD_LIMIT_BYTES + 1024:
        body += repeated_row

    return bytes(body)
