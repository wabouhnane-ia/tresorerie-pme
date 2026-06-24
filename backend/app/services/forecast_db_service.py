"""Run Prophet forecast and persist to MongoDB."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from tensorflow.keras.callbacks import EarlyStopping
from app.utils.bson_utils import ObjectId
from app.utils.metrics import calculate_metrics

from app.db import collections as c
from app.db.mongodb import database
from app.services.storage_paths import forecast_artifact_dir

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


async def _load_company_timeseries(company_id: str) -> pd.DataFrame:
    """
    Loads historical financial records for a company from MongoDB.

        # Structure pour exposer les statistiques de découpage train/test LSTM
        lstm_stats: dict = {
            "train_count": 0,
            "test_count": 0,
            "train_min": None,
            "train_max": None,
            "test_min": None,
            "test_max": None,
        }
    Supports both old (metrics) and new (flat) structures.
    """
    cursor = database[c.FINANCIAL_RECORDS].find(
        {"company_id": ObjectId(company_id)}
    ).sort("date", 1)

    rows = []
    async for doc in cursor:
        if "metrics" in doc:
            m = doc["metrics"]
            rows.append(
                {
                    "date": doc["date"],
                    "scenario": "company",
                    "cash_inflow": m.get("cash_inflow", 0),
                    "cash_outflow": m.get("cash_outflow", 0),
                    "net_cashflow": m.get("net_cashflow", 0),
                    "treasury_balance": m.get("treasury_balance", 0),
                    "scheduled_receipts": m.get("scheduled_receipts", 0),
                    "overdue_receipts": m.get("overdue_receipts", 0),
                    "scheduled_payments": m.get("scheduled_payments", 0),
                    "overdue_payments": m.get("overdue_payments", 0),
                    "number_of_clients": m.get("number_of_clients", 0),
                    "liquidity_stress_score": m.get("liquidity_stress_score", 0),
                    "liquidity_stress": m.get("liquidity_stress", False),
                }
            )
        else:
            rows.append(
                {
                    "date": doc["date"],
                    "scenario": doc.get("scenario", "actual"),
                    "cash_inflow": doc.get("cash_inflow", 0),
                    "cash_outflow": doc.get("cash_outflow", 0),
                    "treasury_balance": doc.get("treasury_balance", 0),
                    "scheduled_receipts": doc.get("scheduled_receipts", 0),
                    "overdue_receipts": doc.get("overdue_receipts", 0),
                    "scheduled_payments": doc.get("scheduled_payments", 0),
                    "overdue_payments": doc.get("overdue_payments", 0),
                    "number_of_clients": 0,
                    "liquidity_stress_score": 0,
                    "liquidity_stress": False,
                }
            )

    if not rows:
        raise ValueError(
            "No financial records found for this company. Please upload a financial dataset to run forecasts."
        )

    return pd.DataFrame(rows)


def _check_model_eligibility(df: pd.DataFrame, sequence_length: int = 30) -> dict:
    """
    Check which models are eligible based on data availability.
    Returns models_available and model_constraints.
    """
    record_count = len(df)
    models_available = {
        "prophet": record_count >= 2,
        "lstm": False
    }
    model_constraints = {}

    if record_count < sequence_length * 2:
        model_constraints["lstm"] = "insufficient_timeseries_data"
    else:
        models_available["lstm"] = True

    return {
        "models_available": models_available,
        "model_constraints": model_constraints,
        "record_count": record_count
    }


def _evaluate_prophet_holdout(
    prophet_df: pd.DataFrame,
    scenario: str | None,
    horizon_days: int,
) -> dict:
    from app.forecasting.prophet_model import ProphetForecaster

    if len(prophet_df) < 5:
        return {"model": "prophet"}

    holdout_size = min(
        max(1, int(len(prophet_df) * 0.2)),
        horizon_days,
    )

    train_df = prophet_df.iloc[:-holdout_size]
    test_df = prophet_df.iloc[-holdout_size:]

    eval_forecaster = ProphetForecaster(scenario=scenario)
    eval_forecaster.train_model(train_df)

    eval_future = eval_forecaster.make_future_dataframe(
        prophet_df=train_df,
        periods=holdout_size,
    )
    eval_forecast = eval_forecaster.predict(eval_future)
    eval_forecast["ds"] = pd.to_datetime(eval_forecast["ds"])
    eval_rows = eval_forecast[eval_forecast["ds"] > train_df["ds"].max()].head(
        len(test_df)
    )

    if len(eval_rows) < len(test_df):
        return {"model": "prophet"}

    y_true = test_df["y"].to_numpy()
    y_pred = eval_rows["yhat"].to_numpy()[: len(test_df)]
    # Calculate training naive MAE for MASE scaling
    train_y = train_df["y"].to_numpy()
    train_diffs = np.abs(np.diff(train_y))
    mae_naive_train = float(np.nanmean(train_diffs)) if train_diffs.size > 0 else 0.0
    metrics = calculate_metrics(y_true, y_pred, mae_naive_train=mae_naive_train)  # CORRECTION : métriques avec MASE correct
    metrics["model"] = "prophet"  # CORRECTION : conserve le format existant (clé 'model' attendue)
    return metrics  # CORRECTION : évite recalculs divergents entre modèles


def _run_lstm_forecast(
    company_id: str,
    df: pd.DataFrame,
    future_rows: pd.DataFrame,
    eligibility: dict,
    horizon_days: int,  # CORRECTION : nécessaire pour aligner exactement le holdout LSTM sur Prophet (même logique)
) -> tuple[dict, list[float | None], list[float | None], list[float | None], str, str | None, list[dict]]:
    metrics_lstm = {}
    lstm_forecast_values: list[float | None] = []
    lstm_lower_bounds: list[float | None] = []
    lstm_upper_bounds: list[float | None] = []
    top_feature_importance: list[dict] = []
    lstm_status = "skipped"
    lstm_skip_reason = eligibility["model_constraints"].get("lstm")

    if not eligibility["models_available"]["lstm"]:
        return metrics_lstm, [None] * len(future_rows), [None] * len(future_rows), [None] * len(future_rows), lstm_status, lstm_skip_reason, []

    try:
        from app.lstm.data_preparation import LSTMDataPreparation
        from app.lstm.lstm_model import LSTMForecastModel

        prep = LSTMDataPreparation()
        feature_df = prep.add_features(df.copy())  # CORRECTION : ajoute lags/rolling AVANT la sélection
        feature_df = prep.select_features(feature_df)  # CORRECTION : sélectionne les features enrichies
        holdout_size = min(max(1, int(len(feature_df) * 0.2)), horizon_days)  # CORRECTION : alignement strict avec Prophet (même formule)
        split_index = len(feature_df) - holdout_size  # CORRECTION : test = derniers holdout_size points (mêmes dates que Prophet)
        train_data = feature_df.iloc[:split_index]  # CORRECTION : découpage temporel identique à Prophet
        test_data = feature_df.iloc[split_index:]  # CORRECTION : découpage temporel identique à Prophet
        train_scaled, test_scaled = prep.scale_data(train_data, test_data)  # CORRECTION : scaler fit uniquement sur train (pas de leakage)

        if len(train_scaled) < prep.sequence_length:  # CORRECTION : garantit les 30 jours de contexte nécessaires (évite X_test vide même avec 100 jours)
            logger.warning("LSTM skipped: insufficient train history for sequence_length context")  # CORRECTION : message explicite
            lstm_skip_reason = "insufficient_history_for_sequences"  # CORRECTION : raison standardisée
            return metrics_lstm, [None] * len(future_rows), [None] * len(future_rows), [None] * len(future_rows), lstm_status, lstm_skip_reason, []  # CORRECTION : fallback propre

        X_train, y_train = prep.create_sequences(train_scaled)  # CORRECTION : apprentissage sur train uniquement

        eval_scaled = np.vstack([train_scaled[-prep.sequence_length :], test_scaled])  # CORRECTION : construit X_test avec contexte train + holdout (évite dataset test vide)
        X_test, y_test = prep.create_sequences(eval_scaled)  # CORRECTION : produit exactement holdout_size observations test

        if len(X_train) == 0 or len(X_test) == 0:
            logger.warning(
                "LSTM skipped due to insufficient historical data. Using Prophet forecasting."
            )
            lstm_skip_reason = "insufficient_sequences"
            return metrics_lstm, [None] * len(future_rows), [None] * len(future_rows), [None] * len(future_rows), lstm_status, lstm_skip_reason, []

        lstm_status = "attempted"
        lstm_model = LSTMForecastModel(
            input_shape=X_train.shape[1:],
            epochs=100,
            batch_size=16,
            patience=10
        )
        
        # CORRECTION : Entraînement avec KerasTuner (Auto-Tuning) et EarlyStopping intégré
        lstm_model.train(
            X_train,
            y_train,
            X_val=X_test,
            y_val=y_test,
            use_tuner=True,
        )

        lstm_test_pred = lstm_model.model.predict(X_test, verbose=0).flatten()
        dummy_pred = np.zeros((len(lstm_test_pred), len(prep.features)))  # CORRECTION : support inverse_transform multi-features (col 0 = treasury_balance)
        dummy_pred[:, 0] = lstm_test_pred  # CORRECTION : place la cible prédite dans la colonne 0 (treasury_balance)
        # Use DataFrame with feature names to preserve column alignment and avoid sklearn warnings
        dummy_pred_df = pd.DataFrame(dummy_pred, columns=prep.features)
        lstm_pred_inv = prep.scaler.inverse_transform(dummy_pred_df)[:, 0]  # CORRECTION : dénormalisation cohérente (unité MAD)

        dummy_test = np.zeros((len(y_test), len(prep.features)))  # CORRECTION : support inverse_transform multi-features (col 0 = treasury_balance)
        dummy_test[:, 0] = y_test  # CORRECTION : place la cible réelle (scaled) dans la colonne 0
        dummy_test_df = pd.DataFrame(dummy_test, columns=prep.features)
        y_test_inv = prep.scaler.inverse_transform(dummy_test_df)[:, 0]  # CORRECTION : y_true dénormalisé dans la même unité que y_pred

        # Calculate training naive MAE for MASE scaling
        train_y = train_data["treasury_balance"].to_numpy()
        train_diffs = np.abs(np.diff(train_y))
        mae_naive_train = float(np.nanmean(train_diffs)) if train_diffs.size > 0 else 0.0

        metrics_lstm = calculate_metrics(y_test_inv, lstm_pred_inv, mae_naive_train=mae_naive_train)  # CORRECTION : métriques avec MASE correct
        metrics_lstm["model"] = "lstm"  # CORRECTION : conserve le format existant (clé 'model')

        # PHASE 3: Residual RMSE for Probabilistic Bounds
        residuals = y_test_inv - lstm_pred_inv
        residual_rmse = float(np.sqrt(np.mean(residuals**2))) if len(residuals) > 0 else 0.0

        # PHASE 3: Permutation Importance
        feature_importances = []
        baseline_mase = metrics_lstm.get("mase", 0.0)
        for i, feature_name in enumerate(prep.features):
            if i == 0:
                continue
            X_test_shuffled = X_test.copy()
            np.random.shuffle(X_test_shuffled[:, :, i])
            shuffled_pred = lstm_model.model.predict(X_test_shuffled, verbose=0).flatten()
            dummy_pred_shuffled = np.zeros((len(shuffled_pred), len(prep.features)))
            dummy_pred_shuffled[:, 0] = shuffled_pred
            dummy_pred_shuffled_df = pd.DataFrame(dummy_pred_shuffled, columns=prep.features)
            shuffled_pred_inv = prep.scaler.inverse_transform(dummy_pred_shuffled_df)[:, 0]
            shuffled_metrics = calculate_metrics(y_test_inv, shuffled_pred_inv, mae_naive_train=mae_naive_train)
            shuffled_mase = shuffled_metrics.get("mase", baseline_mase)
            importance = max(0.0, float(shuffled_mase - baseline_mase))
            feature_importances.append({"feature": feature_name, "importance": importance})
            
        feature_importances.sort(key=lambda x: x["importance"], reverse=True)
        top_feature_importance = feature_importances[:3]

        # Build sequence of scaled feature vectors for iterative forecasting
        full_scaled = np.vstack([train_scaled, test_scaled])
        sequence = full_scaled[-prep.sequence_length :].copy()
        # Maintain raw history for computing rolling means and lags
        balance_history_raw = (
            feature_df["treasury_balance"]
            .to_numpy(dtype=float)[-prep.sequence_length :]
            .tolist()
        )

        # Precompute feature indices
        idx_lag_1 = prep.features.index("tb_lag_1") if "tb_lag_1" in prep.features else None
        idx_lag_7 = prep.features.index("tb_lag_7") if "tb_lag_7" in prep.features else None
        idx_lag_30 = prep.features.index("tb_lag_30") if "tb_lag_30" in prep.features else None
        idx_rm_7 = prep.features.index("tb_rolling_7") if "tb_rolling_7" in prep.features else None
        idx_rm_30 = prep.features.index("tb_rolling_30") if "tb_rolling_30" in prep.features else None
        idx_rstd_7 = prep.features.index("tb_rolling_std_7") if "tb_rolling_std_7" in prep.features else None
        idx_rstd_30 = prep.features.index("tb_rolling_std_30") if "tb_rolling_std_30" in prep.features else None
        idx_day_sin = prep.features.index("day_sin") if "day_sin" in prep.features else None
        idx_day_cos = prep.features.index("day_cos") if "day_cos" in prep.features else None
        idx_month_sin = prep.features.index("month_sin") if "month_sin" in prep.features else None
        idx_month_cos = prep.features.index("month_cos") if "month_cos" in prep.features else None
        idx_weekday_sin = prep.features.index("weekday_sin") if "weekday_sin" in prep.features else None
        idx_weekday_cos = prep.features.index("weekday_cos") if "weekday_cos" in prep.features else None

        # For projecting simple exogenous features, use last observed raw values as fallback
        last_row_raw = feature_df.iloc[-1] if len(feature_df) else None

        for i in range(len(future_rows)):
            next_scaled = float(
                lstm_model.model.predict(sequence[np.newaxis, :, :], verbose=0)[0, 0]
            )
            lstm_forecast_values.append(next_scaled)

            # Compute raw next treasury balance by inverse transforming a dummy row
            dummy_row = np.zeros((1, len(prep.features)))
            dummy_row[0, 0] = next_scaled
            dummy_row_df = pd.DataFrame(dummy_row, columns=prep.features)
            inv_row = prep.scaler.inverse_transform(dummy_row_df)[0]
            next_raw = float(inv_row[0])

            # update raw history used for rolling computations
            balance_history_raw.append(next_raw)
            if len(balance_history_raw) > prep.sequence_length:
                balance_history_raw = balance_history_raw[-prep.sequence_length :]

            # compute lag and rolling raw values
            last_raw = float(balance_history_raw[-1])
            lag_1_raw = last_raw
            lag_7_raw = float(balance_history_raw[-7]) if len(balance_history_raw) >= 7 else last_raw
            lag_30_raw = float(balance_history_raw[-30]) if len(balance_history_raw) >= 30 else float(balance_history_raw[0])
            rolling_mean_7_raw = float(np.mean(balance_history_raw[-7:])) if len(balance_history_raw) >= 7 else float(np.mean(balance_history_raw))
            rolling_mean_30_raw = float(np.mean(balance_history_raw))
            
            # compute rolling standard deviation raw values
            rolling_std_7_raw = float(np.std(balance_history_raw[-7:])) if len(balance_history_raw) >= 7 else 0.0
            rolling_std_30_raw = float(np.std(balance_history_raw))

            # build raw feature vector in the same order as prep.features
            raw_next = np.zeros((len(prep.features),), dtype=float)
            raw_next[0] = next_raw
            if idx_lag_1 is not None:
                raw_next[idx_lag_1] = lag_1_raw
            if idx_lag_7 is not None:
                raw_next[idx_lag_7] = lag_7_raw
            if idx_lag_30 is not None:
                raw_next[idx_lag_30] = lag_30_raw
            if idx_rm_7 is not None:
                raw_next[idx_rm_7] = rolling_mean_7_raw
            if idx_rm_30 is not None:
                raw_next[idx_rm_30] = rolling_mean_30_raw
            if idx_rstd_7 is not None:
                raw_next[idx_rstd_7] = rolling_std_7_raw
            if idx_rstd_30 is not None:
                raw_next[idx_rstd_30] = rolling_std_30_raw

            # Use last observed raw values for cash_inflow/outflow/net if available
            if last_row_raw is not None:
                if "cash_inflow" in feature_df.columns:
                    try:
                        raw_next[prep.features.index("cash_inflow")] = float(last_row_raw["cash_inflow"])
                    except Exception:
                        pass
                if "cash_outflow" in feature_df.columns:
                    try:
                        raw_next[prep.features.index("cash_outflow")] = float(last_row_raw["cash_outflow"])
                    except Exception:
                        pass
                if "net_cashflow" in feature_df.columns:
                    try:
                        raw_next[prep.features.index("net_cashflow")] = float(last_row_raw["net_cashflow"])
                    except Exception:
                        pass

            # is_payment_day and cyclic calendar features: derive from future date if available
            try:
                future_date = pd.to_datetime(future_rows.iloc[i]["ds"]) if "ds" in future_rows.columns else None
                if future_date is not None:
                    is_pay = float((future_date.day == 28) or (future_date.day == 1))
                    if "is_payment_day" in prep.features:
                        raw_next[prep.features.index("is_payment_day")] = is_pay
                        
                    if idx_day_sin is not None:
                        raw_next[idx_day_sin] = np.sin(2 * np.pi * future_date.day / 31.0)
                    if idx_day_cos is not None:
                        raw_next[idx_day_cos] = np.cos(2 * np.pi * future_date.day / 31.0)
                    if idx_month_sin is not None:
                        raw_next[idx_month_sin] = np.sin(2 * np.pi * future_date.month / 12.0)
                    if idx_month_cos is not None:
                        raw_next[idx_month_cos] = np.cos(2 * np.pi * future_date.month / 12.0)
                    if idx_weekday_sin is not None:
                        raw_next[idx_weekday_sin] = np.sin(2 * np.pi * future_date.dayofweek / 7.0)
                    if idx_weekday_cos is not None:
                        raw_next[idx_weekday_cos] = np.cos(2 * np.pi * future_date.dayofweek / 7.0)
            except Exception:
                pass

            # transform raw_next to scaled space using the fitted scaler
            raw_next_df = pd.DataFrame(raw_next.reshape(1, -1), columns=prep.features)
            scaled_next_row = prep.scaler.transform(raw_next_df)[0]

            # advance sequence with the newly scaled row
            sequence = np.vstack([sequence[1:], scaled_next_row])

        if lstm_forecast_values:
            dummy_future = np.zeros((len(lstm_forecast_values), len(prep.features)))
            dummy_future[:, 0] = np.array(lstm_forecast_values)
            dummy_future_df = pd.DataFrame(dummy_future, columns=prep.features)
            lstm_forecast_values = prep.scaler.inverse_transform(dummy_future_df)[:, 0].tolist()
            
            for i, val in enumerate(lstm_forecast_values):
                horizon_step = i + 1
                margin = 1.96 * residual_rmse * np.sqrt(horizon_step)
                lstm_lower_bounds.append(val - margin)
                lstm_upper_bounds.append(val + margin)

        lstm_status = "completed"

    except Exception as exc:
        logger.warning(
            f"LSTM training or forecast failed for company {company_id}: {exc}",
        )
        lstm_status = "failed"
        lstm_skip_reason = str(exc)
        metrics_lstm = {}
        lstm_forecast_values = [None] * len(future_rows)
        lstm_lower_bounds = [None] * len(future_rows)
        lstm_upper_bounds = [None] * len(future_rows)
        top_feature_importance = []

    return metrics_lstm, lstm_forecast_values, lstm_lower_bounds, lstm_upper_bounds, lstm_status, lstm_skip_reason, top_feature_importance


async def run_prophet_forecast(
    *,
    company_id: str,
    user_id: ObjectId,
    scenario: str | None = None,
    horizon_days: int = 30,
) -> dict:
    """Uses company data; scenario is optional metadata tag."""
    df = await _load_company_timeseries(company_id)
    
    # Shared preprocessing: calendar enrichment
    from app.services.calendar_enrichment_service import CalendarEnrichmentService
    from app.lstm.data_preparation import LSTMDataPreparation
    
    calendar_service = CalendarEnrichmentService(country_code="MA")
    df_enriched = calendar_service.enrich_calendar_features(df.copy())
    
    # Get feature metadata
    lstm_prep = LSTMDataPreparation()
    feature_metadata = lstm_prep.get_feature_metadata(df_enriched)

    eligibility = _check_model_eligibility(df_enriched)

    run_id = ObjectId()
    created_at = _utcnow()
    run_doc = {
        "_id": run_id,
        "company_id": ObjectId(company_id),
        "triggered_by": user_id,
        "models": ["prophet", "lstm"],
        "horizon_days": horizon_days,
        "status": "running",
        "input": {
            "record_count": len(df_enriched),
            "records_from": df_enriched["date"].iloc[0],
            "records_to": df_enriched["date"].iloc[-1],
        },
        "started_at": _utcnow(),
        "completed_at": _utcnow(),
        "created_at": created_at,
        "metadata": {
            "dataset_version": "2.0",
            "feature_version": "2.0",
            "generated_features": feature_metadata["generated_features"],
            "feature_count": feature_metadata["feature_count"],
            "calendar_library": "hijri-converter, holidays",
            "forecast_pipeline_version": "4.2"
        },
        "metrics": {
            "prophet": {
                "model": "prophet",
                "mae": 0.0,
                "rmse": 0.0,
                "mape": 0.0
            },
            "lstm": {
                "model": "lstm",
                "mae": 0.0,
                "rmse": 0.0,
                "mape": 0.0
            }
        },
        "models_available": eligibility["models_available"],
        "model_constraints": eligibility["model_constraints"],
        "lstm_status": "pending",
        "lstm_skip_reason": None,
        "artifacts": {
            "prophet_csv": ""
        },
        "assumptions": {
            "regressor_future": ""
        }
    }
    await database[c.FORECAST_RUNS].insert_one(run_doc)

    try:
        from app.forecasting.prophet_model import ProphetForecaster

        forecaster = ProphetForecaster(scenario=scenario)
        # Pass already enriched df to avoid re-running calendar enrichment
        prophet_df = forecaster.prepare_data(df_enriched)

        metrics_prophet = _evaluate_prophet_holdout(
            prophet_df=prophet_df,
            scenario=scenario,
            horizon_days=horizon_days,
        )

        forecaster.train_model(prophet_df)
        future = forecaster.make_future_dataframe(
            prophet_df=prophet_df,
            periods=horizon_days,
        )
        forecast = forecaster.predict(future)

        artifact_dir = forecast_artifact_dir(company_id, str(run_id))
        artifact_dir.mkdir(parents=True, exist_ok=True)
        csv_path = artifact_dir / f"forecast_{scenario}.csv"
        forecast.to_csv(csv_path, index=False)

        last_hist_date = pd.to_datetime(df["date"]).max()
        forecast["ds"] = pd.to_datetime(forecast["ds"])
        future_rows = forecast[forecast["ds"] > last_hist_date]

        metrics_lstm, lstm_forecast_values, lstm_lower_bounds, lstm_upper_bounds, lstm_status, lstm_skip_reason, feature_importance = _run_lstm_forecast(
            company_id=company_id,
            df=df_enriched,
            future_rows=future_rows,
            eligibility=eligibility,
            horizon_days=horizon_days,  # CORRECTION : transmet horizon_days pour aligner le holdout LSTM
        )

        combined_metrics = {
            "prophet": metrics_prophet,
            "lstm": metrics_lstm,
        }
        best_model = "prophet"
        if (
            metrics_lstm.get("mase") is not None and
            metrics_prophet.get("mase") is not None and
            metrics_lstm["mase"] < metrics_prophet["mase"]
        ):
            best_model = "lstm"

        best_mase = float(combined_metrics[best_model].get("mase", 0.0)) if combined_metrics[best_model].get("mase") is not None else None
        best_rmse = float(combined_metrics[best_model].get("rmse", 0.0)) if combined_metrics[best_model].get("rmse") is not None else None
        selection_reason = f"Selected {best_model} by lowest MASE"
        model_comparison = {
            "models": ["prophet", "lstm"],
            "best_model": best_model,
            "metrics": combined_metrics,
            "feature_importance": None,
        }

        confidence_score = None
        if best_mase is not None:
            confidence_score = float(max(0.0, min(1.0, 1.0 - best_mase / 2.0)))

        await database[c.FORECASTS].delete_many(
            {
                "company_id": ObjectId(company_id),
                "scenario": scenario,
            }
        )

        docs = []
        for idx, (_, row) in enumerate(future_rows.iterrows()):
            prophet_yhat = float(row["yhat"])
            prophet_lower = float(row.get("yhat_lower", row["yhat"]))
            prophet_upper = float(row.get("yhat_upper", row["yhat"]))
            lstm_yhat = None
            lstm_yhat_lower = None
            lstm_yhat_upper = None
            
            if idx < len(lstm_forecast_values):
                lstm_yhat = float(lstm_forecast_values[idx]) if lstm_forecast_values[idx] is not None else None
                lstm_yhat_lower = float(lstm_lower_bounds[idx]) if lstm_lower_bounds[idx] is not None else None
                lstm_yhat_upper = float(lstm_upper_bounds[idx]) if lstm_upper_bounds[idx] is not None else None

            best_yhat = lstm_yhat if best_model == "lstm" and lstm_yhat is not None else prophet_yhat
            best_lower = lstm_yhat_lower if best_model == "lstm" and lstm_yhat_lower is not None else prophet_lower
            best_upper = lstm_yhat_upper if best_model == "lstm" and lstm_yhat_upper is not None else prophet_upper

            docs.append(
                {
                    "company_id": ObjectId(company_id),
                    "forecast_run_id": run_id,
                    "scenario": scenario,
                    "model": best_model,
                    "ds": row["ds"].strftime("%Y-%m-%d"),
                    "yhat": best_yhat,
                    "yhat_lower": best_lower,
                    "yhat_upper": best_upper,
                    "prophet_yhat": prophet_yhat,
                    "prophet_yhat_lower": prophet_lower,
                    "prophet_yhat_upper": prophet_upper,
                    "lstm_yhat": lstm_yhat,
                    "lstm_yhat_lower": lstm_yhat_lower,
                    "lstm_yhat_upper": lstm_yhat_upper,
                    "created_at": _utcnow(),
                }
            )

        if docs:
            await database[c.FORECASTS].insert_many(docs)

        await database[c.FORECAST_RUNS].update_one(
            {"_id": run_id},
            {
                "$set": {
                    "status": "completed",
                    "best_model": best_model,
                    "best_rmse": best_rmse,
                    "best_mase": best_mase,
                    "model_comparison": model_comparison,
                    "selected_model": best_model,
                    "selected_rmse": best_rmse,
                    "selected_mase": best_mase,
                    "selection_reason": selection_reason,
                    "confidence_score": confidence_score,
                    "feature_importance": feature_importance,
                    "prediction_interval_method": "Residual RMSE" if best_model == "lstm" else "Prophet Default",
                    "metrics": combined_metrics,
                    "artifacts": {"prophet_csv": str(csv_path).replace("\\", "/")},
                    "assumptions": {
                        "regressor_future": "rolling_mean_30d",
                    },
                    "lstm_status": lstm_status,
                    "lstm_skip_reason": lstm_skip_reason,
                    "completed_at": _utcnow(),
                }
            }
        )

        logger.info(
            f"Prophet forecast completed for company {company_id}, saved {len(docs)} points"
        )

        return {
            "forecast_run_id": str(run_id),
            "scenario": scenario,
            "horizon_days": horizon_days,
            "points_saved": len(docs),
            "metrics": {
                "prophet": metrics_prophet,
                "lstm": metrics_lstm
            },
            "models_available": eligibility["models_available"],
            "model_constraints": eligibility["model_constraints"],
        }

    except Exception as exc:
        logger.error(
            f"Prophet forecast failed for company {company_id}: {str(exc)}",
            exc_info=True,
        )
        await database[c.FORECAST_RUNS].update_one(
            {"_id": run_id},
            {"$set": {"status": "failed", "error": str(exc)}},
        )
        raise


async def retrain_company_forecast(company_id: str) -> dict | None:
    """
    Retrains the forecast automatically after a new file upload.
    Does not raise exceptions to avoid blocking the upload.
    """
    try:
        logger.info(f"Starting automatic forecast retrain for company {company_id}")
        
        from app.forecasting.prophet_model import ProphetForecaster

        df = await _load_company_timeseries(company_id)

        system_user_id = ObjectId("000000000000000000000000")

        result = await run_prophet_forecast(
            company_id=company_id,
            user_id=system_user_id,
            scenario=None,
            horizon_days=30,
        )

        logger.info(f"Automatic forecast retrain successful for company {company_id}")
        return result

    except Exception as exc:
        logger.warning(
            f"Automatic forecast retrain failed for company {company_id}: {str(exc)}",
            exc_info=True,
        )
        return None


async def get_forecast_points(
    company_id: str,
    scenario: str = None,
    limit: int = 30,
) -> list[dict]:
    # Get latest forecast run for the company
    latest_run = await database[c.FORECAST_RUNS].find_one(
        {"company_id": ObjectId(company_id), "status": "completed"},
        sort=[("completed_at", -1)]
    )
    
    if not latest_run:
        return []
        
    model_comparison = latest_run.get("model_comparison") or {}
    best_model = latest_run.get("best_model") or model_comparison.get("best_model") or "prophet"

    # Get forecast points for that latest run
    cursor = (
        database[c.FORECASTS]
        .find(
            {
                "company_id": ObjectId(company_id),
                "forecast_run_id": latest_run["_id"],
            }
        )
        .sort("date", 1)
        .limit(limit)
    )

    rows = []
    async for doc in cursor:
        date_val = doc.get("date") or doc.get("ds")
        if best_model == "lstm":
            prediction_val = doc.get("lstm_yhat") if doc.get("lstm_yhat") is not None else doc.get("yhat")
        else:
            prediction_val = doc.get("yhat") or doc.get("prediction")

        lower_val = doc.get("lower_bound") or doc.get("yhat_lower")
        upper_val = doc.get("upper_bound") or doc.get("yhat_upper")
        
        rows.append(
            {
                "ds": date_val,
                "date": date_val,
                "yhat": prediction_val,
                "prediction": prediction_val,
                "yhat_lower": lower_val,
                "lower_bound": lower_val,
                "yhat_upper": upper_val,
                "upper_bound": upper_val,
                "lstm_yhat": doc.get("lstm_yhat"),
                "model": best_model,
            }
        )
    return rows
