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

## 5. Flutter Installation and Running Instructions

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
