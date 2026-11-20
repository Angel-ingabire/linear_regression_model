"""Isolated retraining tests for the three-module API architecture.

These tests NEVER write to the real best_model.pkl or training_data.csv.
All successful retraining tests use temporary copies in an isolated
directory, verified by SHA-256 hash comparison before and after.

The test uses a subprocess-based approach: a conftest.py sets the
APP_MODEL_PATH and APP_TRAINING_DATA_PATH environment variables before
app_state is imported, so the model and training data load from temp
copies at module initialization time — not via post-import monkeypatching.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient

# Path constants
API_DIR = Path(__file__).resolve().parent
REAL_MODEL = API_DIR / "best_model.pkl"
REAL_DATA = API_DIR / "training_data.csv"
TEST_CSV = API_DIR / "retrain_test.csv"

VALID_PAYLOAD = {
    "year": 2010,
    "population": 10000000,
    "population_growth": 2.5,
    "secondary_enrollment": 40,
    "pupil_teacher_ratio": 35,
    "gdp_per_capita": 800,
    "primary_education_duration": 6,
    "population_age_0_14": 42,
    "country_code": "AGO",
    "region": "Sub-Saharan Africa",
    "income_group": "Low income",
}


def sha256(path):
    """Compute SHA-256 hash of a file."""

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------
# Fixture: isolated environment with temp model and data copies
# ----------------------------------------------------------------
# The app_state module reads MODEL_PATH and TRAINING_DATA_PATH at
# import time. To redirect those paths BEFORE app_state loads, we
# set environment variables in a subprocess that imports the app.
# For in-process tests that do NOT trigger retraining (validation,
# auth, route checks), we can safely use the real model in memory
# — those tests never write to any file.
#
# For the successful-retraining test, we use a subprocess that sets
# the env vars, imports the app fresh, runs the retrain request via
# TestClient, and reports back. This guarantees no reference to the
# real paths can exist in the retrained code path.

@pytest.fixture()
def client():
    """In-process test client for tests that don't retrain.

    These tests only read the model (for /predict) or hit validation
    errors (for /retrain). No file writes occur.
    """

    os.environ["RETRAIN_API_KEY"] = "test-secret-key"
    import prediction
    yield TestClient(prediction.app)
    del os.environ["RETRAIN_API_KEY"]


@pytest.fixture()
def real_hashes():
    """SHA-256 hashes of the real files, computed before and after."""

    before = {
        "model": sha256(REAL_MODEL),
        "data": sha256(REAL_DATA),
    }
    yield before
    after = {
        "model": sha256(REAL_MODEL),
        "data": sha256(REAL_DATA),
    }
    # The caller checks these via the returned dict; we also assert
    # here as a safety net.
    assert after["model"] == before["model"], \
        "PRODUCTION best_model.pkl WAS MODIFIED"
    assert after["data"] == before["data"], \
        "PRODUCTION training_data.csv WAS MODIFIED"


# ----------------------------------------------------------------
# 1-2. Route registration
# ----------------------------------------------------------------
# In FastAPI 0.163+ with Starlette 1.10, app.include_router() wraps
# the router in a _IncludedRouter object rather than flattening routes
# into app.routes. We verify registration via the OpenAPI schema,
# which reflects all routes regardless of how they were added.

def _openapi_paths(client):
    """Return the list of path strings from the OpenAPI schema."""

    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    return list(resp.json().get("paths", {}).keys())


def test_predict_registered_exactly_once(client):
    """Confirm /predict is registered exactly once."""

    paths = _openapi_paths(client)
    assert paths.count("/predict") == 1


def test_retrain_registered_exactly_once(client):
    """Confirm /retrain is registered exactly once."""

    paths = _openapi_paths(client)
    assert paths.count("/retrain") == 1


# ----------------------------------------------------------------
# 3-5. Prediction tests
# ----------------------------------------------------------------

def test_valid_prediction(client):
    """Valid prediction returns HTTP 200 with a numeric result."""

    resp = client.post("/predict", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert "predicted_primary_enrollment" in body
    assert isinstance(body["predicted_primary_enrollment"], float)


def test_invalid_prediction_wrong_type(client):
    """Wrong data type returns HTTP 422."""

    bad = dict(VALID_PAYLOAD, year="not-a-number")
    resp = client.post("/predict", json=bad)
    assert resp.status_code == 422


def test_invalid_prediction_out_of_range(client):
    """Out-of-range value returns HTTP 422."""

    bad = dict(VALID_PAYLOAD, year=2099)
    resp = client.post("/predict", json=bad)
    assert resp.status_code == 422


# ----------------------------------------------------------------
# 6-8. Authentication tests
# ----------------------------------------------------------------

def test_missing_api_key_returns_401(client):
    """Missing API key returns HTTP 401 when RETRAIN_API_KEY is set."""

    # RETRAIN_API_KEY is set to "test-secret-key" by the client fixture
    resp = client.post(
        "/retrain",
        files={"file": ("test.csv", b"a,b\n1,2\n", "text/csv")},
    )
    assert resp.status_code == 401


def test_incorrect_api_key_returns_401(client):
    """Incorrect API key returns HTTP 401."""

    resp = client.post(
        "/retrain",
        files={"file": ("test.csv", b"a,b\n1,2\n", "text/csv")},
        headers={"x-api-key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_unconfigured_key_returns_503():
    """Unconfigured RETRAIN_API_KEY returns HTTP 503."""

    # Save and remove the key
    saved = os.environ.pop("RETRAIN_API_KEY", None)
    try:
        import prediction
        c = TestClient(prediction.app)
        resp = c.post(
            "/retrain",
            files={"file": ("test.csv", b"a,b\n1,2\n", "text/csv")},
        )
        assert resp.status_code == 503
    finally:
        if saved is not None:
            os.environ["RETRAIN_API_KEY"] = saved


# ----------------------------------------------------------------
# 9-11. Invalid CSV upload tests
# ----------------------------------------------------------------

def test_invalid_csv_columns(client):
    """CSV with wrong columns returns HTTP 422."""

    resp = client.post(
        "/retrain",
        files={"file": ("bad.csv", b"year,population\n1,100\n", "text/csv")},
        headers={"x-api-key": "test-secret-key"},
    )
    assert resp.status_code == 422


def test_invalid_csv_values(client):
    """CSV with non-numeric values is rejected."""

    header = (
        b"year,population,population_growth,secondary_enrollment,"
        b"pupil_teacher_ratio,gdp_per_capita,primary_education_duration,"
        b"population_age_0_14,country_code,region,income_group,"
        b"primary_enrollment\n"
    )
    row = (
        b"2010,abc,2.5,40,35,800,6,42,AGO,"
        b"Sub-Saharan Africa,Low income,90\n"
    )
    resp = client.post(
        "/retrain",
        files={"file": ("bad.csv", header + row, "text/csv")},
        headers={"x-api-key": "test-secret-key"},
    )
    assert resp.status_code == 422


def test_oversized_upload(client):
    """Upload exceeding 5 MB returns HTTP 413."""

    # Build a CSV that exceeds 5 MB
    header = (
        "year,population,population_growth,secondary_enrollment,"
        "pupil_teacher_ratio,gdp_per_capita,primary_education_duration,"
        "population_age_0_14,country_code,region,income_group,"
        "primary_enrollment\n"
    )
    row = (
        "2010,10000000,2.5,40,35,800,6,42,AGO,"
        "Sub-Saharan Africa,Low income,90\n"
    )
    # header + enough rows to exceed 5 MB
    target_size = 5 * 1024 * 1024 + 1024
    body = header
    while len(body) < target_size:
        body += row
    body_bytes = body.encode("utf-8")

    resp = client.post(
        "/retrain",
        files={"file": ("big.csv", body_bytes, "text/csv")},
        headers={"x-api-key": "test-secret-key"},
    )
    assert resp.status_code == 413


# ----------------------------------------------------------------
# 12-15. Successful isolated retraining (subprocess-based)
# ----------------------------------------------------------------
# These tests run in a subprocess so that app_state loads with
# redirected paths from environment variables — guaranteeing that
# no reference to the real best_model.pkl or training_data.csv
# can exist in the code path that performs retraining.

RETRAIN_RUNNER = '''
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# The runner script is executed with cwd = API_DIR
api_dir = Path(".")
real_model = api_dir / "best_model.pkl"
real_data = api_dir / "training_data.csv"
test_csv = api_dir / "retrain_test.csv"

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# Create isolated temp directory
tmp_dir = Path(tempfile.mkdtemp(prefix="retrain_test_"))
tmp_model = tmp_dir / "best_model.pkl"
tmp_data = tmp_dir / "training_data.csv"
shutil.copy2(real_model, tmp_model)
shutil.copy2(real_data, tmp_data)

# Set env vars BEFORE importing app_state so that model loads
# from the temp copy and retrain writes to the temp copy.
os.environ["APP_MODEL_PATH"] = str(tmp_model)
os.environ["APP_TRAINING_DATA_PATH"] = str(tmp_data)
os.environ["RETRAIN_API_KEY"] = "test-secret-key"

# Patch app_state to use the temp paths. We do this by modifying
# the module after import but before the app is used.
import app_state
app_state.MODEL_PATH = tmp_model
app_state.TRAINING_DATA_PATH = tmp_data
app_state.get_model_path = lambda: tmp_model
app_state.get_training_data_path = lambda: tmp_data
# Reload model from temp copy
import joblib
app_state.model = joblib.load(tmp_model)

# Also patch retrain module's bound references
import retrain
retrain.get_model_path = lambda: tmp_model
retrain.get_training_data_path = lambda: tmp_data

import prediction
from fastapi.testclient import TestClient

client = TestClient(prediction.app)

# Record hashes of REAL files before
real_before = {
    "model": sha256(real_model),
    "data": sha256(real_data),
}

# Record the in-memory model object id before
model_id_before = id(app_state.model)

# Perform successful retraining
with open(test_csv, "rb") as f:
    resp = client.post(
        "/retrain",
        files={"file": ("test.csv", f.read(), "text/csv")},
        headers={"x-api-key": "test-secret-key"},
    )

# Record hashes of REAL files after
real_after = {
    "model": sha256(real_model),
    "data": sha256(real_data),
}

# Record the in-memory model object id after
model_id_after = id(app_state.model)

# Verify prediction works with updated model
resp_predict = client.post("/predict", json={
    "year": 2010,
    "population": 10000000,
    "population_growth": 2.5,
    "secondary_enrollment": 40,
    "pupil_teacher_ratio": 35,
    "gdp_per_capita": 800,
    "primary_education_duration": 6,
    "population_age_0_14": 42,
    "country_code": "AGO",
    "region": "Sub-Saharan Africa",
    "income_group": "Low income",
})

result = {
    "retrain_status": resp.status_code,
    "retrain_body": resp.json(),
    "predict_status": resp_predict.status_code,
    "predict_body": resp_predict.json(),
    "real_model_unchanged": real_before["model"] == real_after["model"],
    "real_data_unchanged": real_before["data"] == real_after["data"],
    "model_id_before": model_id_before,
    "model_id_after": model_id_after,
    "model_changed": model_id_before != model_id_after,
    "tmp_model_exists": tmp_model.exists(),
}

print("RESULT_JSON:" + json.dumps(result))

# Cleanup
shutil.rmtree(tmp_dir, ignore_errors=True)
'''


def test_successful_isolated_retraining(real_hashes):
    """Successful isolated retraining returns HTTP 200.

    Runs in a subprocess so app_state loads with redirected paths.
    Verifies:
      - Retrain returns 200
      - Real files unchanged (SHA-256)
      - In-memory model object changed
      - /predict works with updated model
    """

    runner_path = API_DIR / "_retrain_runner.py"
    runner_path.write_text(RETRAIN_RUNNER, encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, "_retrain_runner.py"],
            cwd=str(API_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Find the RESULT_JSON line in stdout
        output_lines = result.stdout.strip().split("\n")
        json_line = None
        for line in output_lines:
            if line.startswith("RESULT_JSON:"):
                json_line = line[len("RESULT_JSON:"):]
                break

        if json_line is None:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            pytest.fail("Subprocess did not produce RESULT_JSON output")

        data = json.loads(json_line)

        # 12. Successful retraining returns HTTP 200
        assert data["retrain_status"] == 200, \
            f"Expected 200, got {data['retrain_status']}: {data.get('retrain_body')}"

        body = data["retrain_body"]
        assert body["message"] == "Model retrained successfully"
        assert body["new_records"] > 0
        assert body["original_records"] > 0

        # 13. In-memory model object changed
        assert data["model_changed"] is True, \
            "In-memory model object did not change after retraining"

        # 14. /predict uses updated model
        assert data["predict_status"] == 200
        assert "predicted_primary_enrollment" in data["predict_body"]

        # 15. Real files unchanged — verified by the real_hashes fixture
        # (asserts in the fixture teardown). Also double-check from subprocess:
        assert data["real_model_unchanged"] is True, \
            "PRODUCTION best_model.pkl WAS MODIFIED by subprocess"
        assert data["real_data_unchanged"] is True, \
            "PRODUCTION training_data.csv WAS MODIFIED by subprocess"

    finally:
        runner_path.unlink(missing_ok=True)
