# Predicting Primary School Enrollment Rates in African Countries Using Machine Learning

## 1. Mission and Problem Statement

Primary school enrollment rates across African countries vary widely due to differences
in economic conditions, population growth, and educational resources. This project applies
machine learning to predict gross primary enrollment from demographic and economic indicators,
serving predictions through a FastAPI backend with a Flutter mobile app for data-driven planning.

## 2. Dataset Description and Source

- **Dataset:** World Bank Education Statistics
- **Kaggle URL:** [https://www.kaggle.com/datasets/theworldbank/education-statistics](https://www.kaggle.com/datasets/theworldbank/education-statistics)
- **Coverage:** 50 African countries, 1970–2016
- **Cleaned dataset:** 1,246 observations
- **Target variable:** Gross primary school enrollment ratio (%)
- **Input variables:** 11 numerical and categorical features (`year`, `population`, `population_growth`, `population_age_0_14`, `secondary_enrollment`, `pupil_teacher_ratio`, `primary_education_duration`, `gdp_per_capita`, `country_code`, `region`, `income_group`)
- **Models trained:** SGDRegressor, LinearRegression, DecisionTreeRegressor, RandomForestRegressor
- **Best model:** RandomForestRegressor
- **Best testing MSE:** approximately 62.62

## 3. Public Swagger UI Link

The deployed FastAPI backend is publicly accessible on Render:

- **Swagger UI:** [https://african-enrollment-api.onrender.com/docs](https://african-enrollment-api.onrender.com/docs)
- **OpenAPI spec:** [https://african-enrollment-api.onrender.com/openapi.json](https://african-enrollment-api.onrender.com/openapi.json)

The API exposes two endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/predict` | POST | Accepts 11 input variables and returns `predicted_primary_enrollment` |
| `/retrain` | POST | Accepts a CSV upload (protected by API key) to retrain the model |

## 4. YouTube Demonstration Link

YouTube demonstration: [Link will be added after recording]

## 5. GitHub Project Structure

```
README.md
.gitignore
summative/
├── linear_regression/
│   └── multivariate.ipynb                 # ML notebook: data prep, EDA, model training, evaluation
├── API/                                   # FastAPI backend
│   ├── app_state.py                       # Shared state: schema, paths, in-memory model, locks
│   ├── prediction.py                      # FastAPI app: /predict endpoint, CORS, router registration
│   ├── retrain.py                         # /retrain endpoint: auth, CSV validation, atomic model replacement
│   ├── test_retrain.py                    # 33 pytest tests: routes, validation, auth, isolated retraining
│   ├── api_test_support.py                # Test helpers: isolated workspaces, SHA-256 hashing, CSV builders
│   ├── retrain_isolation_runner.py        # Subprocess runner for successful-retraining isolation test
│   ├── best_model.pkl                     # Saved Random Forest pipeline (9 MB)
│   ├── training_data.csv                  # 996 training records with 11 features + target
│   ├── pyproject.toml                     # Python project config and dependency pins
│   ├── requirements.txt                   # Exported pinned dependencies
│   ├── uv.lock                            # uv lockfile
│   └── (best_model_backup.pkl, retrain_test.csv are gitignored)
├── FlutterApp/african_enrollment_app/     # Flutter mobile application
│   ├── lib/
│   │   ├── main.dart                      # App entry point and theme
│   │   ├── screens/prediction_screen.dart # 4-step wizard form with validation and result display
│   │   └── services/api_service.dart      # HTTP client for /predict endpoint
│   ├── test/
│   │   ├── widget_test.dart               # 7 widget tests
│   │   ├── api_service_test.dart          # 10 API service unit tests
│   │   └── api_integration_test.dart      # 12 full integration tests with mocked HTTP
│   ├── pubspec.yaml                       # Flutter dependencies
│   └── analysis_options.yaml              # Flutter linter configuration
└── pyproject.toml                         # Workspace-level Python config
```

## 6. Render Deployment

The FastAPI backend is deployed as a managed service on Render.

- **Live API URL:** https://african-enrollment-api.onrender.com
- **Swagger UI:** https://african-enrollment-api.onrender.com/docs
- **OpenAPI spec:** https://african-enrollment-api.onrender.com/openapi.json
- **Startup command:** Render runs the application by importing `prediction:app` from the `summative/API` directory (standard `uvicorn prediction:app` invocation, compatible with the existing `pyproject.toml`).
- **Required environment variable:** `RETRAIN_API_KEY` — must be set in the Render dashboard. Without it, the `/retrain` endpoint returns HTTP 503.
- **Security:** The API key value must **never** be committed to GitHub. It is configured exclusively in the Render dashboard's environment variables. The `.gitignore` already excludes `.env` and `.env.*` files.

## 7. Flutter Installation and Running Instructions

### Prerequisites

- [Flutter SDK](https://docs.flutter.dev/get-started/install) (version `^3.10.8`)
- [Android Studio](https://developer.android.com/studio) or a configured Android emulator
- Internet connection (the app calls the Render-hosted prediction API)

### Setup and Commands

```bash
# Navigate to the Flutter project directory
cd summative/FlutterApp/african_enrollment_app

# Install dependencies
flutter pub get

# Run static analysis
flutter analyze

# Run tests
flutter test

# Launch the app on a connected emulator or device
flutter run
```

### Launching on an Android Emulator

1. Open Android Studio and start an Android emulator from the **Device Manager**.
2. Verify the emulator is detected:
   ```bash
   flutter devices
   ```
3. Run the application:
   ```bash
   flutter run
   ```
4. The app launches on **Country Details** (step 1 of 4). Complete all four steps:
   - **Step 1 — Country Details:** Select country code, region, and income group.
   - **Step 2 — Demographics:** Enter year, population, population growth, and ages 0–14 (%).
   - **Step 3 — Education Indicators:** Enter secondary enrollment (%), pupil–teacher ratio, and primary education duration.
   - **Step 4 — Economy & Prediction:** Enter GDP per capita (USD), then tap **Predict Enrollment**.
5. The app sends the 11 variables to the `/predict` endpoint and displays the predicted gross primary enrollment rate as a percentage.
