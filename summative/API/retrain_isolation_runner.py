"""Standalone runner for the successful-retraining isolation test.

Executed as ``python -m retrain_isolation_runner`` from the API directory
by ``test_retrain.py``. It runs in its own interpreter, creates its own
temporary workspace, redirects the application to it with environment
variables *before* importing ``app_state``, then performs one real
retraining request and reports the outcome as JSON on stdout.

Because the redirect happens before the import, the application inside
this process never resolves a path outside the temporary workspace, so a
successful retraining run cannot touch the shipped ``best_model.pkl`` or
``training_data.csv``.
"""

import json
import os
import shutil
from pathlib import Path

import pandas as pd

import api_test_support

RESULT_PREFIX = "RESULT_JSON:"


def _predict_frame(model, payload):
    """Build a one-row DataFrame ordered like the model's features."""

    return pd.DataFrame([payload], columns=list(model.feature_names_in_))


def main():
    workspace = api_test_support.create_isolated_workspace(
        prefix="retrain_runner_",
    )

    model_path, data_path = api_test_support.configure_environment(workspace)

    os.environ[api_test_support.API_KEY_ENV_VAR] = (
        api_test_support.TEST_API_KEY
    )

    production_before = api_test_support.production_hashes()

    # Imported only now, so app_state resolves the redirected paths.
    import app_state
    import prediction
    from fastapi.testclient import TestClient

    resolved_model_path = Path(app_state.get_model_path())
    resolved_data_path = Path(app_state.get_training_data_path())

    # Hard guard: refuse to continue unless both paths are isolated.
    api_test_support.assert_inside(resolved_model_path, workspace)
    api_test_support.assert_inside(resolved_data_path, workspace)

    client = TestClient(prediction.app)

    payload = dict(api_test_support.VALID_PREDICTION_PAYLOAD)
    upload_bytes = api_test_support.build_sample_upload_bytes()

    predict_before = client.post("/predict", json=payload)

    model_before = app_state.get_model()
    file_hash_before = api_test_support.sha256_file(resolved_model_path)
    prediction_from_old_model = float(
        model_before.predict(_predict_frame(model_before, payload))[0]
    )

    retrain_response = client.post(
        "/retrain",
        files={"file": ("retrain_sample.csv", upload_bytes, "text/csv")},
        headers={"x-api-key": api_test_support.TEST_API_KEY},
    )

    model_after = app_state.get_model()
    file_hash_after = api_test_support.sha256_file(resolved_model_path)

    predict_after = client.post("/predict", json=payload)

    prediction_from_new_model = float(
        model_after.predict(_predict_frame(model_after, payload))[0]
    )

    # Anything in the workspace besides the two expected files would be a
    # temporary artefact leaked by the atomic write.
    stray_files = sorted(
        entry.name
        for entry in workspace.iterdir()
        if entry.name not in {
            api_test_support.MODEL_FILENAME,
            api_test_support.DATA_FILENAME,
        }
    )

    production_after = api_test_support.production_hashes()

    endpoint_prediction = predict_after.json()[
        "predicted_primary_enrollment"
    ]

    result = {
        "workspace": str(workspace),
        "resolved_model_path": str(resolved_model_path),
        "resolved_data_path": str(resolved_data_path),
        "model_inside_workspace": api_test_support.is_inside(
            resolved_model_path,
            workspace,
        ),
        "data_inside_workspace": api_test_support.is_inside(
            resolved_data_path,
            workspace,
        ),
        "predict_status_before": predict_before.status_code,
        "predict_body_before": predict_before.json(),
        "retrain_status": retrain_response.status_code,
        "retrain_body": retrain_response.json(),
        "predict_status_after": predict_after.status_code,
        "predict_body_after": predict_after.json(),
        "model_object_changed": model_before is not model_after,
        "model_type_before": type(model_before).__name__,
        "model_type_after": type(model_after).__name__,
        "model_file_hash_before": file_hash_before,
        "model_file_hash_after": file_hash_after,
        "model_file_rewritten": file_hash_before != file_hash_after,
        "prediction_from_old_model": prediction_from_old_model,
        "prediction_from_new_model": prediction_from_new_model,
        "endpoint_matches_new_model": (
            abs(endpoint_prediction - prediction_from_new_model) < 1e-9
        ),
        "old_and_new_predictions_differ": (
            abs(prediction_from_old_model - prediction_from_new_model)
            > 1e-9
        ),
        "stray_workspace_files": stray_files,
        "production_hashes_before": production_before,
        "production_hashes_after": production_after,
        "production_unchanged": production_before == production_after,
    }

    print(RESULT_PREFIX + json.dumps(result))

    shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    main()
