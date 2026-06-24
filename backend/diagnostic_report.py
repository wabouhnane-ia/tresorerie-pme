from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


def _ensure_backend_on_syspath() -> None:
    backend_dir = Path(__file__).resolve().parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))


def _to_datetime_series(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.tz_localize(None)


def _safe_float_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype(float)


def _fmt_num(x) -> str:
    if x is None:
        return "None"
    try:
        if isinstance(x, (np.floating, float)):
            if np.isnan(x):
                return "nan"
        if isinstance(x, (np.integer, int)):
            return str(int(x))
        return f"{float(x):.6f}"
    except Exception:
        return str(x)


def _fmt_money(x) -> str:
    if x is None:
        return "None"
    try:
        xf = float(x)
        if np.isnan(xf):
            return "nan"
        return f"{xf:,.2f} MAD".replace(",", " ")
    except Exception:
        return str(x)


def _describe_block(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    desc = df[cols].describe(percentiles=[0.25, 0.5, 0.75]).T
    return desc[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]


def _iqr_outliers_strict_3x(df: pd.DataFrame, date_col: str, value_col: str) -> dict:
    s = df[value_col].dropna().astype(float)
    q1 = float(s.quantile(0.25))
    q3 = float(s.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 3.0 * iqr
    upper = q3 + 3.0 * iqr
    mask = (df[value_col].astype(float) < lower) | (df[value_col].astype(float) > upper)
    out = df.loc[mask, [date_col, value_col]].copy()
    out[date_col] = _to_datetime_series(out[date_col])
    out = out.sort_values(date_col)
    return {
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower": lower,
        "upper": upper,
        "count_outliers": int(len(out)),
        "outliers": [(str(d.date()), float(v)) for d, v in zip(out[date_col], out[value_col])],
    }


def _pearson_corr_time(values: np.ndarray) -> float:
    x = np.arange(len(values), dtype=float)
    y = values.astype(float)
    x = x[~np.isnan(y)]
    y = y[~np.isnan(y)]
    if len(y) < 2:
        return float("nan")
    try:
        from scipy.stats import pearsonr

        r, _ = pearsonr(x, y)
        return float(r)
    except Exception:
        return float(np.corrcoef(x, y)[0, 1])


def _adf_test(values: np.ndarray) -> dict:
    y = values.astype(float)
    y = y[~np.isnan(y)]
    if len(y) < 10:
        return {"adf_stat": None, "p_value": None, "used_lag": None, "nobs": None}
    from statsmodels.tsa.stattools import adfuller

    stat, pval, used_lag, nobs, _, _ = adfuller(y, autolag="AIC")
    return {
        "adf_stat": float(stat),
        "p_value": float(pval),
        "used_lag": int(used_lag),
        "nobs": int(nobs),
    }


def _durbin_watson(residuals: np.ndarray) -> float | None:
    r = residuals.astype(float)
    r = r[~np.isnan(r)]
    if len(r) < 3:
        return None
    from statsmodels.stats.stattools import durbin_watson

    return float(durbin_watson(r))


def _percentiles_abs_errors(abs_errors: np.ndarray, percentiles: list[int]) -> dict[int, float]:
    e = abs_errors.astype(float)
    e = e[~np.isnan(e)]
    if len(e) == 0:
        return {p: float("nan") for p in percentiles}
    vals = np.percentile(e, percentiles).astype(float).tolist()
    return {p: float(v) for p, v in zip(percentiles, vals)}


def _calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    _ensure_backend_on_syspath()
    from app.utils.metrics import calculate_metrics

    metrics = calculate_metrics(y_true, y_pred)
    out = {}
    for k in ["mae", "rmse", "mape", "r2"]:
        out[k] = metrics.get(k)
    return out


@dataclass
class ModelEval:
    dates: list[pd.Timestamp]
    y_true: np.ndarray
    y_pred: np.ndarray
    y_true_scaled: np.ndarray | None = None
    y_pred_scaled: np.ndarray | None = None
    scaler_min: float | None = None
    scaler_max: float | None = None


def _evaluate_lstm(df: pd.DataFrame, sequence_length: int = 30, epochs: int = 20) -> dict:
    _ensure_backend_on_syspath()
    from app.lstm.data_preparation import LSTMDataPreparation
    from app.lstm.lstm_model import LSTMForecastModel

    prep = LSTMDataPreparation(sequence_length=sequence_length)
    date_series = _to_datetime_series(df["date"]).reset_index(drop=True)
    # Ensure enriched features (lags, rolling) are added before selection
    enriched = prep.add_features(df.copy())
    feature_df = prep.select_features(enriched)
    holdout_size = max(1, int(len(feature_df) * 0.2))
    split_index = len(feature_df) - holdout_size
    train_data = feature_df.iloc[:split_index]
    test_data = feature_df.iloc[split_index:]
    train_scaled, test_scaled = prep.scale_data(train_data, test_data)

    X_train, y_train = prep.create_sequences(train_scaled)

    eval_scaled = np.vstack([train_scaled[-prep.sequence_length :], test_scaled])
    X_test, y_test = prep.create_sequences(eval_scaled)

    if len(X_train) == 0 or len(X_test) == 0:
        return {
            "status": "skipped",
            "reason": "insufficient_sequences",
        }

    model = LSTMForecastModel(input_shape=X_train.shape[1:])
    history = model.model.fit(
        X_train,
        y_train,
        epochs=epochs,
        batch_size=32,
        validation_split=0.1,
        verbose=0,
    )

    y_pred_scaled = model.model.predict(X_test, verbose=0).flatten().astype(float)

    dummy_pred = np.zeros((len(y_pred_scaled), len(prep.features)))
    dummy_pred[:, 0] = y_pred_scaled
    y_pred_inv = prep.scaler.inverse_transform(dummy_pred)[:, 0].astype(float)

    dummy_test = np.zeros((len(y_test), len(prep.features)))
    dummy_test[:, 0] = y_test.astype(float)
    y_true_inv = prep.scaler.inverse_transform(dummy_test)[:, 0].astype(float)

    test_dates = date_series.iloc[split_index:].tolist()
    dates_aligned = test_dates[: len(y_true_inv)]

    metrics = _calculate_metrics(y_true_inv, y_pred_inv)
    residuals = y_true_inv - y_pred_inv
    abs_errors = np.abs(residuals)

    losses = history.history.get("loss", [])
    val_losses = history.history.get("val_loss", [])

    scaler_min = float(prep.scaler.data_min_[0]) if hasattr(prep.scaler, "data_min_") else None
    scaler_max = float(prep.scaler.data_max_[0]) if hasattr(prep.scaler, "data_max_") else None

    p1 = float(np.nanpercentile(train_data.iloc[:, 0].to_numpy(dtype=float), 1))
    p99 = float(np.nanpercentile(train_data.iloc[:, 0].to_numpy(dtype=float), 99))
    ratio = float((p99 - p1) / (scaler_max - scaler_min)) if (scaler_min is not None and scaler_max is not None and scaler_max != scaler_min) else float("nan")

    n_params = int(model.model.count_params())
    n_examples = int(len(X_train))
    params_per_example = float(n_params / n_examples) if n_examples > 0 else float("inf")

    worst_idx = np.argsort(abs_errors)[-5:][::-1]
    worst = []
    for i in worst_idx:
        if i < len(dates_aligned):
            worst.append(
                {
                    "date": str(pd.to_datetime(dates_aligned[i]).date()),
                    "y_true": float(y_true_inv[i]),
                    "y_pred": float(y_pred_inv[i]),
                    "abs_error": float(abs_errors[i]),
                }
            )

    return {
        "status": "ok",
        "features": prep.features,
        "sequence_length": prep.sequence_length,
        "metrics": metrics,
        "learning_curve": {
            "loss": [float(x) for x in losses],
            "val_loss": [float(x) for x in val_losses],
        },
        "residuals": {
            "mean": float(np.mean(residuals)),
            "std": float(np.std(residuals)),
            "min": float(np.min(residuals)),
            "max": float(np.max(residuals)),
            "durbin_watson": _durbin_watson(residuals),
            "worst_5": worst,
            "abs_error_percentiles": _percentiles_abs_errors(abs_errors, [50, 75, 90, 95, 99]),
        },
        "scaler": {
            "treasury_balance_data_min": scaler_min,
            "treasury_balance_data_max": scaler_max,
            "p99_p1_over_range_ratio": ratio,
        },
        "denorm_check": {
            "y_test_scaled_0": float(y_test[0]) if len(y_test) > 0 else None,
            "y_test_inv_0": float(y_true_inv[0]) if len(y_true_inv) > 0 else None,
            "y_true_original_0": float(test_data.iloc[0, 0]) if len(test_data) > 0 else None,
            "date_0": str(pd.to_datetime(test_dates[0]).date()) if len(test_dates) > 0 else None,
        },
        "architecture": {
            "layers": [
                {
                    "name": layer.__class__.__name__,
                    "units": int(getattr(layer, "units", 0)) if getattr(layer, "units", None) is not None else None,
                    "activation": str(getattr(layer, "activation", None).__name__) if getattr(layer, "activation", None) is not None else None,
                }
                for layer in model.model.layers
            ],
            "total_params": n_params,
            "train_examples": n_examples,
            "params_per_example": params_per_example,
        },
    }


def _evaluate_prophet(df: pd.DataFrame, horizon_days: int | None = None) -> dict:
    _ensure_backend_on_syspath()
    from app.forecasting.prophet_model import ProphetForecaster

    forecaster = ProphetForecaster(scenario=None)
    prophet_df = forecaster.prepare_data(df)
    prophet_df = prophet_df.sort_values("ds")
    holdout_size = max(1, int(len(prophet_df) * 0.2))
    if horizon_days is not None:
        holdout_size = min(holdout_size, int(horizon_days))

    train_df = prophet_df.iloc[:-holdout_size]
    test_df = prophet_df.iloc[-holdout_size:]
    forecaster.train_model(train_df)

    future = forecaster.make_future_dataframe(prophet_df=train_df, periods=holdout_size)
    forecast = forecaster.predict(future)
    forecast["ds"] = pd.to_datetime(forecast["ds"])

    eval_rows = forecast[forecast["ds"] > train_df["ds"].max()].head(len(test_df))
    if len(eval_rows) < len(test_df):
        return {"status": "skipped", "reason": "insufficient_eval_rows"}

    y_true = test_df["y"].to_numpy(dtype=float)
    y_pred = eval_rows["yhat"].to_numpy(dtype=float)[: len(y_true)]
    metrics = _calculate_metrics(y_true, y_pred)
    residuals = y_true - y_pred
    abs_errors = np.abs(residuals)

    cps = []
    try:
        changepoints = list(forecaster.model.changepoints)
        deltas = None
        try:
            deltas = forecaster.model.params.get("delta")
        except Exception:
            deltas = None
        if deltas is not None and len(deltas.shape) == 2 and deltas.shape[1] == len(changepoints):
            delta_mean = deltas.mean(axis=0).astype(float).tolist()
        else:
            delta_mean = [float("nan")] * len(changepoints)
        for dt, amp in zip(changepoints, delta_mean):
            cps.append({"date": str(pd.to_datetime(dt).date()), "delta_mean": float(amp)})
    except Exception:
        cps = []

    worst_idx = np.argsort(abs_errors)[-5:][::-1]
    worst = []
    dates = test_df["ds"].tolist()
    for i in worst_idx:
        if i < len(dates):
            worst.append(
                {
                    "date": str(pd.to_datetime(dates[i]).date()),
                    "y_true": float(y_true[i]),
                    "y_pred": float(y_pred[i]),
                    "abs_error": float(abs_errors[i]),
                }
            )

    return {
        "status": "ok",
        "metrics": metrics,
        "changepoints": cps,
        "residuals": {
            "mean": float(np.mean(residuals)),
            "std": float(np.std(residuals)),
            "min": float(np.min(residuals)),
            "max": float(np.max(residuals)),
            "durbin_watson": _durbin_watson(residuals),
            "worst_5": worst,
            "abs_error_percentiles": _percentiles_abs_errors(abs_errors, [50, 75, 90, 95, 99]),
        },
        "train_tail_regressor_means": {r: float(train_df[r].tail(30).mean()) for r in ["cash_inflow", "cash_outflow", "number_of_clients", "liquidity_stress_score"] if r in train_df.columns},
        "test_regressors": {
            r: test_df[r].to_numpy(dtype=float).tolist()
            for r in ["cash_inflow", "cash_outflow", "number_of_clients", "liquidity_stress_score"]
            if r in test_df.columns
        },
    }


def _regressor_projection_error(prophet_eval: dict) -> dict:
    means = prophet_eval.get("train_tail_regressor_means") or {}
    test_regs = prophet_eval.get("test_regressors") or {}
    out = {}
    for r, series in test_regs.items():
        y_true = np.array(series, dtype=float)
        proj = np.full_like(y_true, float(means.get(r, 0.0)), dtype=float)
        mae = float(np.mean(np.abs(y_true - proj))) if len(y_true) else float("nan")
        denom = float(np.mean(np.abs(y_true))) if len(y_true) else float("nan")
        rel = float(mae / denom) if denom not in (0.0, float("nan")) and denom == denom else float("nan")
        out[r] = {"mae": mae, "relative_mae": rel}
    return out


def _seasonality_strength(df: pd.DataFrame, value_col: str) -> dict:
    d = df.copy()
    d["date_dt"] = _to_datetime_series(d["date"])
    s = d[value_col].astype(float)
    overall_std = float(np.nanstd(s.to_numpy(dtype=float)))
    by_dow = d.groupby(d["date_dt"].dt.dayofweek)[value_col].mean().astype(float)
    by_month = d.groupby(d["date_dt"].dt.month)[value_col].mean().astype(float)
    weekly_strength = float(np.nanstd(by_dow.to_numpy(dtype=float)) / overall_std) if overall_std > 0 else float("nan")
    monthly_strength = float(np.nanstd(by_month.to_numpy(dtype=float)) / overall_std) if overall_std > 0 else float("nan")
    return {
        "overall_std": overall_std,
        "weekday_means": {int(k): float(v) for k, v in by_dow.to_dict().items()},
        "month_means": {int(k): float(v) for k, v in by_month.to_dict().items()},
        "weekly_strength_ratio": weekly_strength,
        "monthly_strength_ratio": monthly_strength,
    }


def _baseline_metrics(df: pd.DataFrame, target_col: str) -> dict:
    s = df[target_col].astype(float).to_numpy()
    holdout_size = max(1, int(len(s) * 0.2))
    train = s[:-holdout_size]
    test = s[-holdout_size:]
    naive_1 = np.roll(test, 1)
    naive_1[0] = train[-1] if len(train) else test[0]
    naive_mean = np.full_like(test, float(np.nanmean(train)), dtype=float)
    return {
        "holdout_size": int(holdout_size),
        "naive_1": _calculate_metrics(test, naive_1),
        "naive_mean": _calculate_metrics(test, naive_mean),
        "train_mean": float(np.nanmean(train)),
        "test_mean": float(np.nanmean(test)),
    }


def _print_section(title: str) -> None:
    print()
    print(title)


def _print_diagnostic(name: str, result_lines: list[str], problem: str, severity: str, impact: str, recommendation: str) -> None:
    print()
    print(f"### {name}")
    for line in result_lines:
        print(f"- Résultat : {line}")
    print(f"- Problème : {problem}")
    print(f"- Sévérité : {severity}")
    print(f"- Impact sur les métriques : {impact}")
    print(f"- Correction recommandée : {recommendation}")


async def main_async(company_id: str) -> int:
    _ensure_backend_on_syspath()
    from app.services.forecast_db_service import _load_company_timeseries

    df = await _load_company_timeseries(company_id)
    df = df.copy()
    df["date"] = _to_datetime_series(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    cols = ["treasury_balance", "cash_inflow", "cash_outflow", "net_cashflow", "liquidity_stress_score"]
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = _safe_float_series(df[c])

    _print_section("===================================================")
    _print_section("## BLOC 1 — QUALITÉ DES DONNÉES")
    _print_section("===================================================")

    desc = _describe_block(df, cols)
    _print_diagnostic(
        "📊 1.1 Statistiques descriptives",
        [desc.to_string()],
        "NON",
        "🟢 Faible",
        "Contexte de distribution pour interpréter RMSE/MAE et détecter les échelles.",
        "Aucune (diagnostic).",
    )

    nulls = df[cols + ["date"]].isnull().sum()
    zeros = {c: int((df[c] == 0).sum()) for c in cols}
    _print_diagnostic(
        "🧩 1.2 Valeurs nulles / manquantes",
        [nulls.to_string(), f"zéros_par_colonne={zeros}"],
        "OUI" if int(nulls.sum()) > 0 else "NON",
        "🟠 Élevé" if int(nulls.sum()) > 0 else "🟢 Faible",
        "Des NaN/None peuvent casser le scaler, Prophet, et biaiser les métriques.",
        "Imputer ou corriger la source BD; distinguer 0 réel vs valeur manquante.",
    )

    date_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    present = pd.to_datetime(df["date"]).dt.normalize()
    missing = date_range.difference(present)
    missing_list = [str(d.date()) for d in missing]
    _print_diagnostic(
        "📅 1.3 Gaps temporels (jours manquants)",
        [f"nb_jours_manquants={len(missing_list)}", f"dates_manquantes={missing_list}"],
        "OUI" if len(missing_list) > 0 else "NON",
        "🟠 Élevé" if len(missing_list) > 0 else "🟢 Faible",
        "Des trous créent des ruptures artificielles et dégradent les modèles séquentiels.",
        "Reconstituer les jours manquants (forward-fill ciblé) ou corriger l’ingestion.",
    )

    out_tb = _iqr_outliers_strict_3x(df, "date", "treasury_balance")
    out_ncf = _iqr_outliers_strict_3x(df, "date", "net_cashflow")
    _print_diagnostic(
        "🚨 1.4 Outliers (IQR strict 3×IQR)",
        [
            f"treasury_balance: Q1={_fmt_money(out_tb['q1'])}, Q3={_fmt_money(out_tb['q3'])}, IQR={_fmt_money(out_tb['iqr'])}, bornes=[{_fmt_money(out_tb['lower'])}, {_fmt_money(out_tb['upper'])}], nb_outliers={out_tb['count_outliers']}, outliers={out_tb['outliers']}",
            f"net_cashflow: Q1={_fmt_money(out_ncf['q1'])}, Q3={_fmt_money(out_ncf['q3'])}, IQR={_fmt_money(out_ncf['iqr'])}, bornes=[{_fmt_money(out_ncf['lower'])}, {_fmt_money(out_ncf['upper'])}], nb_outliers={out_ncf['count_outliers']}, outliers={out_ncf['outliers']}",
        ],
        "OUI" if (out_tb["count_outliers"] > 0 or out_ncf["count_outliers"] > 0) else "NON",
        "🟠 Élevé" if out_tb["count_outliers"] > 0 else ("🟡 Moyen" if out_ncf["count_outliers"] > 0 else "🟢 Faible"),
        "Des outliers peuvent écraser MinMaxScaler (LSTM) et déplacer les changepoints (Prophet).",
        "Valider les jours extrêmes; winsoriser ou changer de scaler si nécessaire.",
    )

    solde_initial = float(df["treasury_balance"].iloc[0]) if len(df) else 0.0
    treasury_recalc = solde_initial + df["net_cashflow"].cumsum()
    corr = float(df["treasury_balance"].corr(treasury_recalc))
    diff = (df["treasury_balance"] - treasury_recalc).abs()
    top10 = df.loc[diff.sort_values(ascending=False).head(10).index, ["date", "treasury_balance", "net_cashflow"]].copy()
    top10["treasury_recalc"] = treasury_recalc.loc[top10.index].values
    top10["abs_diff"] = diff.loc[top10.index].values
    top10 = top10.sort_values("abs_diff", ascending=False)
    _print_diagnostic(
        "🧮 1.5 Cohérence de treasury_balance (recalc via cumsum net_cashflow)",
        [f"corr={_fmt_num(corr)}", top10.to_string(index=False)],
        "OUI" if corr < 0.95 else "NON",
        "🔴 Critique" if corr < 0.95 else "🟢 Faible",
        "Si treasury_balance est incohérent, la cible contient du bruit structurel → métriques et forecasts dégradés.",
        "Recalculer/valider treasury_balance en BD; corriger la logique d’agrégation.",
    )

    corr_time = _pearson_corr_time(df["treasury_balance"].to_numpy(dtype=float))
    trend_label = "oscillante"
    if abs(corr_time) >= 0.90:
        trend_label = "quasi monotone"
    elif abs(corr_time) >= 0.60:
        trend_label = "tendance modérée"
    _print_diagnostic(
        "📈 1.6 Tendance générale",
        [f"corr_time_pearson={_fmt_num(corr_time)}", f"interpretation={trend_label}"],
        "PARTIEL" if abs(corr_time) >= 0.60 else "NON",
        "🟡 Moyen" if abs(corr_time) >= 0.60 else "🟢 Faible",
        "Une tendance forte non modélisée correctement fait chuter R² (surtout Prophet).",
        "Introduire des features de tendance (lags/rolling) ou un modèle avec intégration/diff.",
    )

    adf = _adf_test(df["treasury_balance"].to_numpy(dtype=float))
    pval = adf.get("p_value")
    non_stationary = (pval is not None) and (pval > 0.05)
    _print_diagnostic(
        "🧪 1.7 Stationnarité (ADF)",
        [
            f"adf_stat={_fmt_num(adf.get('adf_stat'))}",
            f"p_value={_fmt_num(pval)}",
            f"used_lag={_fmt_num(adf.get('used_lag'))}",
            f"nobs={_fmt_num(adf.get('nobs'))}",
        ],
        "OUI" if non_stationary else "NON",
        "🟠 Élevé" if non_stationary else "🟢 Faible",
        "Une série non stationnaire rend l’apprentissage plus difficile et peut casser Prophet si la tendance est mal contrainte.",
        "Différencier / modéliser le niveau (balance) via lags/returns; ajuster la priors/trend.",
    )

    _print_section("===================================================")
    _print_section("## BLOC 2 — QUALITÉ DES FEATURES")
    _print_section("===================================================")

    corr_mat = df[cols].corr(method="pearson")
    corr_with_target = corr_mat["treasury_balance"].drop("treasury_balance")
    useless = corr_with_target[abs(corr_with_target) < 0.1].to_dict()
    redundant = []
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            v = float(corr_mat.loc[a, b])
            if abs(v) > 0.9:
                redundant.append((a, b, v))
    _print_diagnostic(
        "🧬 2.1 Matrice de corrélation complète",
        [corr_mat.to_string(), f"features_corr_target_lt_0_1={useless}", f"features_corr_pair_gt_0_9={redundant}"],
        "PARTIEL" if (len(useless) > 0 or len(redundant) > 0) else "NON",
        "🟡 Moyen" if (len(useless) > 0 or len(redundant) > 0) else "🟢 Faible",
        "Features peu corrélées ou redondantes peuvent ajouter du bruit sans signal.",
        "Élaguer/redéfinir features; ajouter lags/rolling plus informatifs.",
    )

    dfeat = df.copy()
    dfeat["lag_1"] = dfeat["treasury_balance"].shift(1)
    dfeat["lag_7"] = dfeat["treasury_balance"].shift(7)
    dfeat["lag_30"] = dfeat["treasury_balance"].shift(30)
    dfeat["rolling_7"] = dfeat["treasury_balance"].rolling(7).mean()
    dfeat["rolling_30"] = dfeat["treasury_balance"].rolling(30).mean()
    dfeat["rolling_std7"] = dfeat["treasury_balance"].rolling(7).std()
    dfeat["day_of_week"] = dfeat["date"].dt.dayofweek.astype(float)
    dfeat["month"] = dfeat["date"].dt.month.astype(float)
    dfeat["is_end_month"] = dfeat["date"].dt.is_month_end.astype(int).astype(float)
    if "number_of_clients" in dfeat.columns:
        dfeat["number_of_clients"] = _safe_float_series(dfeat["number_of_clients"])

    candidate_cols = [
        "lag_1",
        "lag_7",
        "lag_30",
        "rolling_7",
        "rolling_30",
        "rolling_std7",
        "day_of_week",
        "month",
        "is_end_month",
    ]
    if "number_of_clients" in dfeat.columns:
        candidate_cols.append("number_of_clients")

    corr_candidates = {}
    for cc in candidate_cols:
        tmp = dfeat[["treasury_balance", cc]].dropna()
        if len(tmp) < 3:
            corr_candidates[cc] = float("nan")
        else:
            corr_candidates[cc] = float(tmp["treasury_balance"].corr(tmp[cc]))
    ranked = sorted(corr_candidates.items(), key=lambda kv: (abs(kv[1]) if kv[1] == kv[1] else -1), reverse=True)
    _print_diagnostic(
        "🧠 2.2 Features potentielles manquantes (corrélation)",
        [f"corr_candidates={corr_candidates}", f"ranked_by_abs_corr={ranked}"],
        "PARTIEL",
        "🟠 Élevé",
        "Sans lags/rolling, Prophet projette mal et le LSTM peut manquer de structure explicite.",
        f"Ajouter en priorité (top corr absolue): {ranked[:5]}",
    )

    rf_df = df.copy()
    rf_df["treasury_balance_lag1"] = rf_df["treasury_balance"].shift(1)
    rf_features = ["treasury_balance_lag1", "cash_inflow", "cash_outflow", "net_cashflow", "liquidity_stress_score"]
    rf_df = rf_df.dropna(subset=rf_features + ["treasury_balance"])
    holdout_size = max(1, int(len(rf_df) * 0.2))
    train_rf = rf_df.iloc[:-holdout_size]
    test_rf = rf_df.iloc[-holdout_size:]
    from sklearn.ensemble import RandomForestRegressor

    rf = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(train_rf[rf_features].to_numpy(dtype=float), train_rf["treasury_balance"].to_numpy(dtype=float))
    importances = rf.feature_importances_.astype(float).tolist()
    rf_ranked = sorted(zip(rf_features, importances), key=lambda x: x[1], reverse=True)
    _print_diagnostic(
        "🌲 2.3 Importance des features (Random Forest proxy)",
        [f"feature_importances_ranked={rf_ranked}"],
        "PARTIEL",
        "🟡 Moyen",
        "Si 1-2 features dominent, les autres ajoutent surtout du bruit et peuvent dégrader le LSTM.",
        "Supprimer/pondérer les features faibles; ajouter features de structure (rolling/seasonality).",
    )

    _print_section("===================================================")
    _print_section("## BLOC 3 — DIAGNOSTIC DU MODÈLE LSTM")
    _print_section("===================================================")

    lstm_eval = _evaluate_lstm(df, sequence_length=30, epochs=20)
    if lstm_eval.get("status") != "ok":
        _print_diagnostic(
            "🧠 3.x LSTM (évaluation)",
            [f"status={lstm_eval.get('status')}", f"reason={lstm_eval.get('reason')}"],
            "OUI",
            "🔴 Critique",
            "Impossible de diagnostiquer sans séquences suffisantes.",
            "Augmenter l’historique ou réduire sequence_length.",
        )
    else:
        lc = lstm_eval["learning_curve"]
        curve_lines = []
        for i in range(min(len(lc["loss"]), len(lc["val_loss"]))):
            curve_lines.append(f"epoch={i+1} loss={_fmt_num(lc['loss'][i])} val_loss={_fmt_num(lc['val_loss'][i])}")
        overfit = False
        if len(lc["val_loss"]) >= 5:
            tail = lc["val_loss"][-5:]
            overfit = tail[-1] > min(tail)
        _print_diagnostic(
            "📉 3.1 Courbe d'apprentissage complète",
            curve_lines,
            "OUI" if overfit else "NON",
            "🟠 Élevé" if overfit else "🟢 Faible",
            "Overfitting = val_loss remonte → généralisation dégradée et RMSE/MAE augmentent.",
            "EarlyStopping + régularisation (dropout/L2) + features plus stables.",
        )

        res = lstm_eval["residuals"]
        _print_diagnostic(
            "🧾 3.2 Analyse des résidus (holdout)",
            [
                f"mean={_fmt_money(res['mean'])}",
                f"std={_fmt_money(res['std'])}",
                f"min={_fmt_money(res['min'])}",
                f"max={_fmt_money(res['max'])}",
                f"durbin_watson={_fmt_num(res['durbin_watson'])}",
                f"worst_5={res['worst_5']}",
            ],
            "PARTIEL" if (res["durbin_watson"] is not None and abs(res["durbin_watson"] - 2.0) > 0.5) else "NON",
            "🟡 Moyen" if (res["durbin_watson"] is not None and abs(res["durbin_watson"] - 2.0) > 0.5) else "🟢 Faible",
            "Résidus autocorrélés = modèle manque une structure temporelle → erreurs systématiques.",
            "Ajouter lags/rolling/seasonality explicites ou architecture plus adaptée.",
        )

        _print_diagnostic(
            "📦 3.3 Distribution des erreurs",
            [f"abs_error_percentiles={res['abs_error_percentiles']}"],
            "PARTIEL",
            "🟡 Moyen",
            "Quelques jours extrêmes peuvent gonfler RMSE même si SMAPE reste faible.",
            "Identifier les pires jours (événements) et ajouter variables exogènes/flags.",
        )

        sc = lstm_eval["scaler"]
        outlier_squash = sc["p99_p1_over_range_ratio"] == sc["p99_p1_over_range_ratio"] and sc["p99_p1_over_range_ratio"] < 0.8
        _print_diagnostic(
            "🧪 3.4 Problème du scaler (MinMax)",
            [
                f"treasury_balance_data_min={_fmt_money(sc['treasury_balance_data_min'])}",
                f"treasury_balance_data_max={_fmt_money(sc['treasury_balance_data_max'])}",
                f"(p99-p1)/(max-min)={_fmt_num(sc['p99_p1_over_range_ratio'])}",
            ],
            "OUI" if outlier_squash else "NON",
            "🟠 Élevé" if outlier_squash else "🟢 Faible",
            "Si un outlier écrase la normalisation, le LSTM apprend sur une échelle déformée → RMSE/MAE augmentent.",
            "Tester RobustScaler/QuantileTransformer ou traiter les outliers.",
        )

        dn = lstm_eval["denorm_check"]
        _print_diagnostic(
            "🔁 3.5 Vérification de la dénormalisation",
            [
                f"date_0={dn['date_0']}",
                f"y_test_scaled_0={_fmt_num(dn['y_test_scaled_0'])}",
                f"y_test_inv_0={_fmt_money(dn['y_test_inv_0'])}",
                f"y_true_original_0={_fmt_money(dn['y_true_original_0'])}",
            ],
            "OUI" if (dn["y_test_inv_0"] is not None and dn["y_true_original_0"] is not None and abs(float(dn["y_test_inv_0"]) - float(dn["y_true_original_0"])) > 1e-6) else "NON",
            "🔴 Critique" if (dn["y_test_inv_0"] is not None and dn["y_true_original_0"] is not None and abs(float(dn["y_test_inv_0"]) - float(dn["y_true_original_0"])) > 1e-6) else "🟢 Faible",
            "Une dénormalisation incorrecte fausse directement RMSE/MAE et la cohérence métier des prédictions.",
            "Aligner scaler/features et vérifier l’index 0 de la cible partout.",
        )

        arch = lstm_eval["architecture"]
        _print_diagnostic(
            "🏗️ 3.6 Architecture actuelle vs recommandée",
            [
                f"layers={arch['layers']}",
                f"total_params={arch['total_params']}",
                f"train_examples={arch['train_examples']}",
                f"params_per_example={_fmt_num(arch['params_per_example'])}",
            ],
            "PARTIEL",
            "🟡 Moyen",
            "Trop de paramètres vs peu d’exemples = surapprentissage; trop peu = sous-apprentissage.",
            "Adapter la capacité (units/layers) et ajouter régularisation + features de structure.",
        )

    _print_section("===================================================")
    _print_section("## BLOC 4 — DIAGNOSTIC DE PROPHET")
    _print_section("===================================================")

    prophet_eval = _evaluate_prophet(df)
    if prophet_eval.get("status") != "ok":
        _print_diagnostic(
            "🧙 4.x Prophet (évaluation)",
            [f"status={prophet_eval.get('status')}", f"reason={prophet_eval.get('reason')}"],
            "OUI",
            "🔴 Critique",
            "Impossible de diagnostiquer Prophet sans evaluation holdout.",
            "Vérifier la préparation des données et la taille du holdout.",
        )
    else:
        _print_diagnostic(
            "🧭 4.1 Analyse de la tendance (changepoints)",
            [f"changepoints_count={len(prophet_eval['changepoints'])}", f"changepoints={prophet_eval['changepoints']}"],
            "PARTIEL",
            "🟡 Moyen",
            "Changepoints mal placés ou trop nombreux = surajustement de tendance → R² chute en holdout.",
            "Ajuster changepoint_prior_scale / désactiver saisonnalités non pertinentes.",
        )

        proj_err = _regressor_projection_error(prophet_eval)
        bad_regs = {k: v for k, v in proj_err.items() if v["relative_mae"] == v["relative_mae"] and v["relative_mae"] > 0.2}
        _print_diagnostic(
            "🧮 4.2 Erreur de projection des regressors (rolling_mean_30j)",
            [f"projection_error={proj_err}", f"regressors_relative_mae_gt_0_2={bad_regs}"],
            "OUI" if len(bad_regs) > 0 else "NON",
            "🔴 Critique" if len(bad_regs) > 0 else "🟢 Faible",
            "Si les regressors futurs sont mal projetés, Prophet extrapole sur de faux signaux → R² très négatif.",
            "Prédire les regressors (modèles dédiés) ou utiliser des scénarios/valeurs futures réelles.",
        )

        seas = _seasonality_strength(df, "treasury_balance")
        weekly_fake = seas["weekly_strength_ratio"] == seas["weekly_strength_ratio"] and seas["weekly_strength_ratio"] < 0.05
        yearly_fake = seas["monthly_strength_ratio"] == seas["monthly_strength_ratio"] and seas["monthly_strength_ratio"] < 0.05
        _print_diagnostic(
            "🌀 4.3 Saisonnalité (signal réel vs fictif)",
            [
                f"weekly_strength_ratio(std_weekday_means/overall_std)={_fmt_num(seas['weekly_strength_ratio'])}",
                f"monthly_strength_ratio(std_month_means/overall_std)={_fmt_num(seas['monthly_strength_ratio'])}",
                f"weekday_means={seas['weekday_means']}",
                f"month_means={seas['month_means']}",
            ],
            "OUI" if (weekly_fake or yearly_fake) else "NON",
            "🟠 Élevé" if (weekly_fake or yearly_fake) else "🟢 Faible",
            "Des saisonnalités fictives ajoutent du bruit et dégradent l’erreur de projection.",
            "Désactiver weekly/yearly si le signal est faible, ou fournir features de calendrier mieux adaptées.",
        )

        pres = prophet_eval["residuals"]
        _print_diagnostic(
            "🧾 4.4 Résidus Prophet (holdout)",
            [
                f"mean={_fmt_money(pres['mean'])}",
                f"std={_fmt_money(pres['std'])}",
                f"min={_fmt_money(pres['min'])}",
                f"max={_fmt_money(pres['max'])}",
                f"durbin_watson={_fmt_num(pres['durbin_watson'])}",
                f"worst_5={pres['worst_5']}",
                f"abs_error_percentiles={pres['abs_error_percentiles']}",
            ],
            "PARTIEL",
            "🟠 Élevé",
            "Des résidus structurés indiquent que Prophet rate la dynamique (niveau/tendance/regressors).",
            "Revoir target, cap/floor, trend priors, et surtout la projection des regressors.",
        )

    _print_section("===================================================")
    _print_section("## BLOC 5 — MÉTRIQUES : INTERPRÉTATION MÉTIER")
    _print_section("===================================================")

    mean_balance = float(np.nanmean(df["treasury_balance"].to_numpy(dtype=float)))
    lstm_rmse = lstm_eval.get("metrics", {}).get("rmse") if lstm_eval.get("status") == "ok" else None
    rel_rmse = float(lstm_rmse / mean_balance * 100.0) if (lstm_rmse is not None and mean_balance != 0) else None
    _print_diagnostic(
        "💼 5.1 Interprétation du RMSE en contexte métier",
        [f"mean_treasury_balance={_fmt_money(mean_balance)}", f"rmse_lstm={_fmt_money(lstm_rmse)}", f"rmse_over_mean_pct={_fmt_num(rel_rmse)}%"],
        "PARTIEL",
        "🟡 Moyen",
        "Un RMSE faible en % du solde moyen peut être acceptable même si la valeur absolue paraît élevée.",
        "Définir un seuil métier (ex: <3% du solde moyen) et alerter si dépassement.",
    )

    holdout_size = max(1, int(len(df) * 0.2))
    y_holdout = df["treasury_balance"].to_numpy(dtype=float)[-holdout_size:]
    var_holdout = float(np.nanvar(y_holdout))
    r2_lstm = lstm_eval.get("metrics", {}).get("r2") if lstm_eval.get("status") == "ok" else None
    unexplained_var = float((1.0 - float(r2_lstm)) * var_holdout) if (r2_lstm is not None) else None
    unexplained_std = float(np.sqrt(unexplained_var)) if (unexplained_var is not None and unexplained_var >= 0) else None
    _print_diagnostic(
        "📐 5.2 Interprétation du R²",
        [f"r2_lstm={_fmt_num(r2_lstm)}", f"var_holdout={_fmt_num(var_holdout)}", f"unexplained_var={( _fmt_num(unexplained_var) )}", f"sqrt_unexplained_var={_fmt_money(unexplained_std)}"],
        "PARTIEL",
        "🟡 Moyen",
        "Le (1-R²)×Var traduit la part de variance non expliquée; sa racine est un ordre de grandeur d’erreur structurelle.",
        "Réduire la variance non expliquée via features exogènes (événements, calendriers) et lags/rolling.",
    )

    baselines = _baseline_metrics(df, "treasury_balance")
    _print_diagnostic(
        "🏁 5.3 Benchmark naïf (baseline)",
        [
            f"holdout_size={baselines['holdout_size']}",
            f"naive_1_metrics={baselines['naive_1']}",
            f"naive_mean_metrics={baselines['naive_mean']}",
            f"train_mean={_fmt_money(baselines['train_mean'])}",
            f"test_mean={_fmt_money(baselines['test_mean'])}",
            f"lstm_metrics={lstm_eval.get('metrics') if lstm_eval.get('status') == 'ok' else None}",
            f"prophet_metrics={prophet_eval.get('metrics') if prophet_eval.get('status') == 'ok' else None}",
        ],
        "PARTIEL",
        "🟠 Élevé",
        "Si un baseline naïf fait presque aussi bien, le gain modèle est faible et l’amélioration doit venir des features/projection.",
        "Comparer systématiquement à Naive_1; viser un gain clair sur RMSE et SMAPE.",
    )

    _print_section("")
    _print_section("## TABLEAU DE SYNTHÈSE FINAL")
    print("| # | Problème | Sévérité | Impact | Correction prioritaire |")
    print("|---|----------|----------|--------|------------------------|")
    summary_rows = []
    if corr < 0.95:
        summary_rows.append(("Incohérence treasury_balance vs cumsum(net_cashflow)", "🔴", "R² ↓, RMSE/MAE ↑", "Corriger calcul/agrégation en BD"))
    if prophet_eval.get("status") == "ok":
        bad_regs = {k: v for k, v in _regressor_projection_error(prophet_eval).items() if v["relative_mae"] == v["relative_mae"] and v["relative_mae"] > 0.2}
        if len(bad_regs) > 0:
            summary_rows.append(("Projection regressors Prophet erronée (>20%)", "🔴", "R² très négatif", "Prédire regressors / fournir valeurs futures réalistes"))
    if out_tb["count_outliers"] > 0:
        summary_rows.append(("Outliers treasury_balance (IQR 3×) potentiellement écrasants", "🟠", "Scaler + Prophet changepoints", "Traitement outliers / scaler robuste"))
    if non_stationary:
        summary_rows.append(("Série non stationnaire (ADF p>0.05)", "🟠", "Apprentissage plus difficile", "Diff/returns + features de niveau"))
    if len(missing_list) > 0:
        summary_rows.append(("Jours manquants dans la série", "🟠", "Séquences incohérentes", "Reconstituer calendrier quotidien"))
    if len(summary_rows) == 0:
        summary_rows.append(("Aucun problème critique détecté par ces tests", "🟢", "—", "Améliorer via features avancées + tuning"))
    for i, (p, s, imp, fix) in enumerate(summary_rows, start=1):
        print(f"| {i} | {p} | {s} | {imp} | {fix} |")

    _print_section("")
    _print_section("## CONCLUSION FINALE")
    causes = []
    if corr < 0.95:
        causes.append(f"cohérence treasury_balance faible (corr={_fmt_num(corr)})")
    if prophet_eval.get("status") == "ok":
        proj_err = _regressor_projection_error(prophet_eval)
        bad = {k: v for k, v in proj_err.items() if v['relative_mae'] == v['relative_mae'] and v['relative_mae'] > 0.2}
        if len(bad) > 0:
            causes.append(f"projection des regressors Prophet mauvaise (relative_mae>0.2 sur {list(bad.keys())}, détails={bad})")
    if out_tb["count_outliers"] > 0:
        causes.append(f"outliers treasury_balance (nb={out_tb['count_outliers']})")
    if non_stationary:
        causes.append(f"non-stationnarité (ADF p={_fmt_num(pval)})")
    if len(causes) == 0:
        causes = ["signal principal déjà capturé par LSTM, Prophet pénalisé par hypothèses de regressors/saisonnalités"]

    print("Les prédictions sont mauvaises principalement à cause de :")
    for i, ccc in enumerate(causes[:3], start=1):
        print(f"{i}. {ccc}")
    print()
    print("Pour passer de R²=0.56 à R²>0.85, les corrections prioritaires sont :")
    print("1. Ajouter des features de structure (lags/rolling) et/ou modéliser la variation (diff) plutôt que le niveau brut.")
    print("2. Remplacer la projection constante des regressors Prophet par des valeurs futures réalistes (ou désactiver ces regressors).")
    print("3. Traiter les outliers et valider la cohérence comptable de treasury_balance en amont (pipeline BD).")

    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--company-id", required=True, help="MongoDB company_id (ObjectId string)")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    return asyncio.run(main_async(args.company_id))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
