"""
Evaluation metrics for time series forecasting models.
"""
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from typing import Dict, Any


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    mae_naive_train: float = None,
) -> Dict[str, float]:
    """
    Calculate evaluation metrics for forecasting models.

    Args:
        y_true: Ground truth values
        y_pred: Predicted values
        mae_naive_train: Optional naive MAE computed on training set

    Returns:
        Dictionary containing MAE, RMSE, MAPE, SMAPE, R² and MASE
    """
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)

    denom_floor = 1000.0  # CORRECTION : plancher anti-zéro adapté aux montants en MAD (évite explosion du MAPE sur petites valeurs)
    denom = np.where(np.abs(y_true) < denom_floor, denom_floor, np.abs(y_true))  # CORRECTION : remplace le seuil 1e-6 par 1000 MAD
    mape_legacy = np.mean(np.abs((y_true - y_pred) / denom)) * 100  # CORRECTION : MAPE stabilisé (legacy) pour audit/traçabilité

    epsilon = 1e-8  # CORRECTION : epsilon pour éviter 0/0 dans SMAPE (stable sur valeurs nulles)
    smape = 100.0 * np.mean(  # CORRECTION : SMAPE (symétrique, borné ~0..200), plus adapté à net_cashflow autour de zéro
        2.0 * np.abs(y_true - y_pred) / (np.abs(y_true) + np.abs(y_pred) + epsilon)
    )
    mape = smape  # CORRECTION : compatibilité API — le champ 'mape' expose désormais le SMAPE (métrique principale recommandée)

    # MASE utilized for scientific evaluation and model selection
    # MAE_naive = mean(|y_t - y_{t-1}|) (one-step naive forecast on training/true series)
    mae_naive = mae_naive_train
    if mae_naive is None or mae_naive <= 0.0:
        try:
            # fallback to one-step naive forecast errors on y_true
            naive_errors = np.abs(np.diff(np.asarray(y_true, dtype=float)))
            mae_naive = float(np.nanmean(naive_errors)) if naive_errors.size > 0 else 0.0
        except Exception:
            mae_naive = 0.0

    # protect against division by zero
    if mae_naive is None or mae_naive == 0.0:
        mase = None
    else:
        mase = float(mae) / float(mae_naive)

    return {
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "mape": round(float(mape), 2),
        "smape": round(float(smape), 2),  # CORRECTION : expose explicitement le SMAPE sans casser les consommateurs existants
        "mape_legacy": round(float(mape_legacy), 2),  # CORRECTION : conserve le MAPE classique stabilisé (utile pour comparaison/historique)
        "r2": round(float(r2), 4),
        "mase": round(float(mase), 4) if mase is not None else None,
    }

