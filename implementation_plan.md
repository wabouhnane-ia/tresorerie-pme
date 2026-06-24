# Implementation Plan - ML Forecasting Upgrades & MASE-Based Selection

We are upgrading the machine learning forecasting models and updating the model selection criteria from RMSE to MASE.

## User Review Required

> [!IMPORTANT]
> **Shift to MASE (Mean Absolute Scaled Error)**: 
> We are changing the model selection logic in both the active [forecast_db_service.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/services/forecast_db_service.py) and the legacy [model_selector.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/models/model_selector.py) to select the forecasting model with the lowest MASE instead of RMSE.
>
> **Database Fields**: 
> In `forecast_runs`, we will keep the old `best_rmse` / `selected_rmse` fields (populating them for backward compatibility) but add new `best_mase` and `selected_mase` fields to represent the new selection metric.

## Proposed Changes

### Component 1: Evaluation Metrics
We will review [metrics.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/utils/metrics.py) to ensure MASE calculation is correct, robust, and handles edge cases (like zero naive error denominator).

#### [MODIFY] [metrics.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/utils/metrics.py)
* Review and keep `calculate_metrics` returning the `"mase"` key.

---

### Component 2: Prophet Model Upgrades
We will add Moroccan holiday effects to Prophet since the target market uses MAD currency.

#### [MODIFY] [prophet_model.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/forecasting/prophet_model.py)
* Add country holidays configuration for Morocco (`add_country_holidays(country_name='MA')`).

#### [MODIFY] [prophet_model.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/models/prophet_model.py)
* Add the same country holidays config to the unified Prophet model under the models folder.

---

### Component 3: LSTM Model & Data Prep Upgrades
We will optimize the default LSTM layers, regularizations, and data preparation.

#### [MODIFY] [data_preparation.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/lstm/data_preparation.py)
* Enhance preprocessing with additional features (e.g. rolling std, sinusoidal calendar features).
* Integrate `RobustScaler` as the default.

#### [MODIFY] [lstm_model.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/models/lstm_model.py)
* Update default layer configuration (`[32, 16]` units with `0.3` dropout) to prevent overfitting on shorter SME histories, matching the optimization parameters.

---

### Component 4: Model Selector & DB Forecast Service
We will change the model selection logic from RMSE to MASE.

#### [MODIFY] [model_selector.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/models/model_selector.py)
* Change default `primary_metric` from `"rmse"` to `"mase"`.

#### [MODIFY] [forecasting_pipeline.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/models/forecasting_pipeline.py)
* Change model selector initialization metric to `"mase"`.

#### [MODIFY] [forecast_db_service.py](file:///c:/Users/barbo/tresorerie-pme/backend/app/services/forecast_db_service.py)
* Change the comparison from `rmse` to `mase` in `_run_lstm_forecast` and the final selection block in `run_prophet_forecast`.
* Write `best_mase` and `selected_mase` keys into the MongoDB `forecast_runs` collection, while preserving `best_rmse` for schema compatibility.
* Alight selection reasoning to `Selected {best_model} by lowest MASE`.

---

## Verification Plan

### Automated Tests
* Run `python validate_corrections.py` to ensure all structural constraints are correct. (We will first update `validate_corrections.py` to target the active model paths).
* Run `pytest` or existing tests.

### Manual Verification
* Run a mock forecast training run using one of the seed scripts or admin routes.
* Inspect MongoDB records in `forecast_runs` to verify `best_mase`, `best_rmse`, and the selection decision.
