"""API tests for the three-module architecture and isolated retraining.

Isolation strategy
------------------
``app_state`` resolves its model and training-data paths once, at import,
from ``APP_MODEL_PATH`` and ``APP_TRAINING_DATA_PATH``. This module sets
those variables to copies inside a temporary workspace *before* importing
``app_state``, so the application under test holds no reference at all to
the shipped ``best_model.pkl`` or ``training_data.csv``.

The successful-retraining case additionally runs in its own interpreter
(``retrain_isolation_runner.py``) with a temporary workspace of its own,
so a real fit/dump/replace cycle is exercised with no chance of writing
to the repository's files.

An autouse fixture hashes both shipped files after every test and fails
the suite if either byte changes.
"""

import json
import subprocess
import sys

import pytest

import api_test_support as support

# ------------------------------------------------------------------
# Redirect the application to an isolated workspace BEFORE it loads.
# ------------------------------------------------------------------

ISOLATED_WORKSPACE = support.create_isolated_workspace()

ISOLATED_MODEL_PATH, ISOLATED_DATA_PATH = support.configure_environment(
    ISOLATED_WORKSPACE,
)

import app_state  # noqa: E402  (must follow the environment setup)
import prediction  # noqa: E402  (must follow the environment setup)
from fastapi.testclient import TestClient  # noqa: E402


def _verify_app_is_isolated():
    """Abort the whole suite if the app can reach production files."""

    for label, path in (
        ("model", app_state.get_model_path()),
        ("training data", app_state.get_training_data_path()),
    ):
        if not support.is_inside(path, ISOLATED_WORKSPACE):
            raise RuntimeError(
                f"Refusing to run tests: app_state resolves the {label} "
                f"path to {path}, which is outside the isolated "
                f"workspace {ISOLATED_WORKSPACE}."
            )


_verify_app_is_isolated()

BASELINE_PRODUCTION_HASHES = support.production_hashes()


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Test client bound to the application under test."""

    return TestClient(prediction.app)


@pytest.fixture(autouse=True)
def production_files_untouched():
    """Fail any test that modifies the shipped model or training data."""

    before = support.production_hashes()

    yield

    after = support.production_hashes()

    assert after == before, (
        "The shipped best_model.pkl or training_data.csv changed during "
        f"the test run: {before} -> {after}"
    )
    assert after == BASELINE_PRODUCTION_HASHES, (
        "The shipped files no longer match the hashes recorded at the "
        "start of the session."
    )


@pytest.fixture()
def retrain_api_key(monkeypatch):
    """Configure a known retraining API key for the duration of a test."""

    monkeypatch.setenv(support.API_KEY_ENV_VAR, support.TEST_API_KEY)

    return support.TEST_API_KEY


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _upload(content, filename="upload.csv", api_key=None):
    """Build the ``files`` mapping and headers for a retrain request."""

    files = {"file": (filename, content, "text/csv")}

    headers = {}

    if api_key is not None:
        headers["x-api-key"] = api_key

    return files, headers


# With Starlette 1.10 (fastapi >= 0.163), ``include_router`` does not
# flatten the router's routes into ``app.routes``: it appends a
# ``fastapi.routing._IncludedRouter`` that keeps the included APIRouter
# on ``original_router``. The walker therefore descends through any
# nested route container so the counts reflect the true registrations.

_ROUTE_CONTAINER_ATTRIBUTES = ("routes", "original_router", "router", "app")

_MAX_ROUTE_DEPTH = 6


def _child_route_containers(route):
    """Yield the nested route containers held by ``route``.

    ``callable`` is deliberately not used as a filter: both ``APIRouter``
    and ``APIRoute`` are callable because they double as ASGI apps.
    """

    for attribute in _ROUTE_CONTAINER_ATTRIBUTES:
        child = getattr(route, attribute, None)

        if child is None:
            continue

        if isinstance(child, (list, tuple)):
            yield child

        elif hasattr(child, "routes") or hasattr(child, "original_router"):
            yield child


def _collect_route_paths(container, collected, seen=None, depth=0):
    """Collect every registered path found under ``container``."""

    if depth > _MAX_ROUTE_DEPTH:
        return collected

    if seen is None:
        seen = set()

    # Guard against visiting the same router through two attributes.
    if id(container) in seen:
        return collected

    seen.add(id(container))

    routes = getattr(container, "routes", container)

    if not isinstance(routes, (list, tuple)):
        return collected

    for route in routes:
        path = getattr(route, "path", None)

        if isinstance(path, str):
            collected.append(path)

        for child in _child_route_containers(route):
            _collect_route_paths(child, collected, seen, depth + 1)

    return collected


def _registered_paths():
    """Return every route path registered on the application."""

    return _collect_route_paths(prediction.app.routes, [])


# ------------------------------------------------------------------
# 1-2. Route registration
# ------------------------------------------------------------------

def test_predict_route_registered_exactly_once(client):
    """``/predict`` must be registered exactly once."""

    assert _registered_paths().count("/predict") == 1

    openapi_paths = client.get("/openapi.json").json()["paths"]

    assert list(openapi_paths).count("/predict") == 1


def test_retrain_route_registered_exactly_once(client):
    """``/retrain`` must be registered exactly once."""

    assert _registered_paths().count("/retrain") == 1

    openapi_paths = client.get("/openapi.json").json()["paths"]

    assert list(openapi_paths).count("/retrain") == 1


def test_openapi_schema_lists_both_endpoints(client):
    """The OpenAPI schema exposes both endpoints as POST operations."""

    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "post" in paths["/predict"]
    assert "post" in paths["/retrain"]


def test_application_uses_isolated_paths():
    """The application under test must not resolve production paths."""

    assert support.is_inside(
        app_state.get_model_path(),
        ISOLATED_WORKSPACE,
    )

    assert support.is_inside(
        app_state.get_training_data_path(),
        ISOLATED_WORKSPACE,
    )

    assert app_state.get_model_path() == ISOLATED_MODEL_PATH
    assert app_state.get_training_data_path() == ISOLATED_DATA_PATH

    assert app_state.get_model_path() != support.PRODUCTION_MODEL_PATH
    assert app_state.get_training_data_path() != support.PRODUCTION_DATA_PATH
# ------------------------------------------------------------------
# 3-5. Prediction
# ------------------------------------------------------------------

def test_valid_prediction_returns_200(client):
    """A valid payload returns HTTP 200 and a numeric prediction."""

    response = client.post(
        "/predict",
        json=support.VALID_PREDICTION_PAYLOAD,
    )

    assert response.status_code == 200

    body = response.json()

    assert set(body) == {"predicted_primary_enrollment"}
    assert isinstance(body["predicted_primary_enrollment"], float)


@pytest.mark.parametrize(
    "field,value",
    [
        ("year", "not-a-year"),
        ("population", "large"),
        ("population_growth", True),
        ("primary_education_duration", "six"),
        ("country_code", 123),
    ],
)
def test_invalid_prediction_types_return_422(client, field, value):
    """Wrong field types must be rejected with HTTP 422."""

    payload = dict(support.VALID_PREDICTION_PAYLOAD, **{field: value})

    assert client.post("/predict", json=payload).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("year", 2099),
        ("year", 1900),
        ("population", 0.0),
        ("population_growth", 42.0),
        ("secondary_enrollment", -1.0),
        ("primary_education_duration", 12),
        ("population_age_0_14", 150.0),
    ],
)
def test_out_of_range_prediction_values_return_422(client, field, value):
    """Out-of-range values must be rejected with HTTP 422."""

    payload = dict(support.VALID_PREDICTION_PAYLOAD, **{field: value})

    assert client.post("/predict", json=payload).status_code == 422


def test_unsupported_category_returns_422(client):
    """Unknown categorical values must be rejected with HTTP 422."""

    payload = dict(support.VALID_PREDICTION_PAYLOAD, country_code="ZZZ")

    assert client.post("/predict", json=payload).status_code == 422


def test_unexpected_field_returns_422(client):
    """Extra fields are forbidden by the prediction schema."""

    payload = dict(support.VALID_PREDICTION_PAYLOAD, extra_field=1)

    assert client.post("/predict", json=payload).status_code == 422


# ------------------------------------------------------------------
# 6-8. Retraining authentication
# ------------------------------------------------------------------

def test_missing_api_key_returns_401(client, retrain_api_key):
    """A missing API key returns HTTP 401 when one is configured."""

    files, headers = _upload(support.build_sample_upload_bytes())

    response = client.post("/retrain", files=files, headers=headers)

    assert response.status_code == 401


def test_incorrect_api_key_returns_401(client, retrain_api_key):
    """An incorrect API key returns HTTP 401."""

    files, headers = _upload(
        support.build_sample_upload_bytes(),
        api_key="definitely-the-wrong-key",
    )

    response = client.post("/retrain", files=files, headers=headers)

    assert response.status_code == 401


def test_unconfigured_api_key_returns_503(client, monkeypatch):
    """No configured RETRAIN_API_KEY means retraining is unavailable."""

    monkeypatch.delenv(support.API_KEY_ENV_VAR, raising=False)

    files, headers = _upload(
        support.build_sample_upload_bytes(),
        api_key="any-key",
    )

    response = client.post("/retrain", files=files, headers=headers)

    assert response.status_code == 503


# ------------------------------------------------------------------
# 9-10. Uploaded CSV validation
# ------------------------------------------------------------------

def test_invalid_csv_columns_return_422(client, retrain_api_key):
    """A CSV whose columns do not match the feature set is rejected."""

    files, headers = _upload(
        support.build_wrong_columns_upload_bytes(),
        api_key=retrain_api_key,
    )

    response = client.post("/retrain", files=files, headers=headers)

    assert response.status_code == 422
    assert "columns" in response.json()["detail"]


@pytest.mark.parametrize(
    "builder",
    [
        support.build_non_numeric_upload_bytes,
        support.build_out_of_range_upload_bytes,
        support.build_negative_target_upload_bytes,
    ],
    ids=["non-numeric", "out-of-range", "negative-target"],
)
def test_invalid_csv_values_are_rejected(client, retrain_api_key, builder):
    """Structurally valid CSVs with bad values are rejected with 422."""

    files, headers = _upload(builder(), api_key=retrain_api_key)

    response = client.post("/retrain", files=files, headers=headers)

    assert response.status_code == 422


def test_non_csv_upload_returns_400(client, retrain_api_key):
    """A non-CSV filename is rejected before parsing."""

    files, headers = _upload(
        support.build_sample_upload_bytes(),
        filename="upload.txt",
        api_key=retrain_api_key,
    )

    response = client.post("/retrain", files=files, headers=headers)

    assert response.status_code == 400


def test_oversized_upload_returns_413(client, retrain_api_key):
    """An upload larger than 5 MB is rejected with HTTP 413."""

    oversized = support.build_oversized_upload_bytes()

    assert len(oversized) > support.UPLOAD_LIMIT_BYTES

    files, headers = _upload(oversized, api_key=retrain_api_key)

    response = client.post("/retrain", files=files, headers=headers)

    assert response.status_code == 413
# ------------------------------------------------------------------
# 11. Concurrent retraining
# ------------------------------------------------------------------

def test_simultaneous_retraining_returns_409(client, retrain_api_key):
    """A second retraining request while one is running gets HTTP 409."""

    files, headers = _upload(
        support.build_sample_upload_bytes(),
        api_key=retrain_api_key,
    )

    # Simulate an in-flight retraining run by holding the lock.
    acquired = app_state.retrain_lock.acquire(blocking=False)

    assert acquired, "Could not acquire retrain_lock for the test"

    try:
        response = client.post(
            "/retrain",
            files=files,
            headers=headers,
        )
    finally:
        app_state.retrain_lock.release()

    assert response.status_code == 409
    assert "progress" in response.json()["detail"].lower()

    # The lock must be free again for later retraining attempts.
    assert app_state.retrain_lock.acquire(blocking=False)

    app_state.retrain_lock.release()


# ------------------------------------------------------------------
# 12-15. Successful retraining in an isolated interpreter
# ------------------------------------------------------------------

RUNNER_MODULE = "retrain_isolation_runner"

RESULT_PREFIX = "RESULT_JSON:"

RUNNER_TIMEOUT_SECONDS = 900


@pytest.fixture(scope="module")
def isolated_retrain_result():
    """Run one isolated retraining cycle and share the outcome.

    All 12-15 checks inspect the same run, so a fresh interpreter (and a
    full model reload) is not spawned once per assertion.
    """

    return _run_isolated_retraining()


def _run_isolated_retraining():
    """Execute the retraining runner in a fresh interpreter."""

    completed = subprocess.run(
        [sys.executable, "-m", RUNNER_MODULE],
        cwd=str(support.API_DIR),
        capture_output=True,
        text=True,
        timeout=RUNNER_TIMEOUT_SECONDS,
    )

    assert completed.returncode == 0, (
        "The isolated retraining runner failed.\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )

    result_line = None

    for line in completed.stdout.splitlines():
        if line.startswith(RESULT_PREFIX):
            result_line = line[len(RESULT_PREFIX):]

    assert result_line is not None, (
        "The runner produced no RESULT_JSON line.\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )

    return json.loads(result_line)


def test_successful_retraining_returns_200(isolated_retrain_result):
    """A valid, isolated retraining run returns HTTP 200."""

    result = isolated_retrain_result

    assert result["retrain_status"] == 200, result["retrain_body"]

    body = result["retrain_body"]

    assert body["message"] == "Model retrained successfully"
    assert body["new_records"] > 0
    assert body["original_records"] > 0
    assert body["total_training_records"] == (
        body["original_records"] + body["new_records"]
    )
    assert body["model_type"] == "RandomForestRegressor"


def test_in_memory_model_changes_after_retraining(isolated_retrain_result):
    """The in-memory model object is replaced by a new instance."""

    result = isolated_retrain_result

    assert result["retrain_status"] == 200, result["retrain_body"]

    assert result["model_object_changed"] is True, (
        "The in-memory model was not replaced after retraining"
    )

    assert result["model_type_before"] == result["model_type_after"]
    assert result["model_file_rewritten"] is True, (
        "The saved model file was not replaced on disk"
    )

    # The atomic write must not leave temporary files behind.
    assert result["stray_workspace_files"] == []


def test_predict_uses_the_updated_model(isolated_retrain_result):
    """``/predict`` serves predictions from the retrained model."""

    result = isolated_retrain_result

    assert result["retrain_status"] == 200, result["retrain_body"]

    assert result["predict_status_before"] == 200
    assert result["predict_status_after"] == 200

    assert "predicted_primary_enrollment" in result["predict_body_after"]

    # The endpoint's answer must equal the new in-memory model's answer,
    # which can only hold if the endpoint read the replaced reference.
    assert result["endpoint_matches_new_model"] is True, result


def test_retraining_never_touches_production_files(isolated_retrain_result):
    """Both shipped files stay byte-for-byte identical."""

    before = support.production_hashes()

    assert before == BASELINE_PRODUCTION_HASHES

    result = isolated_retrain_result

    assert result["model_inside_workspace"] is True
    assert result["data_inside_workspace"] is True

    assert result["production_unchanged"] is True, (
        "The isolated runner reported a change to a production file"
    )

    assert result["production_hashes_before"] == before
    assert result["production_hashes_after"] == before

    after = support.production_hashes()

    assert after == before, (
        "best_model.pkl or training_data.csv changed during the "
        "isolated retraining test"
    )
