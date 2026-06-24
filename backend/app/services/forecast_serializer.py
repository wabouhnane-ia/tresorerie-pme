"""
Central serialization layer for forecast responses.
Converts all numpy, pandas, and MongoDB types to JSON-compatible Python types.
"""

from typing import Any, Dict, List
import numpy as np
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Try to import ObjectId, but don't fail if bson is not available
try:
    from bson import ObjectId
    HAS_BSON = True
except (ImportError, ModuleNotFoundError):
    HAS_BSON = False
    ObjectId = None


def serialize_value(value: Any) -> Any:
    """
    Recursively convert any value to JSON-compatible Python type.
    
    Handles:
    - numpy.float64, numpy.int64, numpy.bool_ → native Python types
    - pandas.Timestamp → ISO format string
    - datetime → ISO format string
    - ObjectId → string
    - list/dict → recursively serialized
    - None → None (preserved)
    
    Args:
        value: Any value to serialize
        
    Returns:
        JSON-compatible Python value
    """
    if value is None:
        return None
    
    # Handle numpy types
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    
    # Handle pandas Timestamp
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    
    # Handle datetime
    if isinstance(value, datetime):
        return value.isoformat()
    
    # Handle ObjectId
    if HAS_BSON and ObjectId and isinstance(value, ObjectId):
        return str(value)
    
    # Handle lists recursively
    if isinstance(value, list):
        return [serialize_value(v) for v in value]
    
    # Handle tuples as lists
    if isinstance(value, tuple):
        return [serialize_value(v) for v in value]
    
    # Handle dicts recursively
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    
    # Return as-is for native Python types
    return value


def serialize_forecast_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize complete forecast response for API output.
    
    Ensures all values are JSON-compatible before Pydantic validation.
    
    Args:
        data: Raw forecast response from pipeline
        
    Returns:
        Serialized response ready for Pydantic validation
    """
    if not isinstance(data, dict):
        logger.warning(f"Expected dict, got {type(data)}")
        return {}
    
    try:
        serialized = serialize_value(data)
        if not isinstance(serialized, dict):
            logger.warning(f"Serialization produced non-dict: {type(serialized)}")
            return {}
        return serialized
    except Exception as e:
        logger.error(f"Serialization failed: {e}", exc_info=True)
        return {}


def safe_get_nested(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely access nested dictionary values.
    
    Args:
        data: Dictionary to access
        *keys: Sequence of keys to traverse
        default: Default value if key not found
        
    Returns:
        Value at nested key or default
        
    Example:
        safe_get_nested(data, "model_comparison", "metrics", default={})
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
    return current if current is not None else default


def ensure_list(value: Any, default: List = None) -> List:
    """
    Ensure value is a list, return default if None.
    
    Args:
        value: Value to check
        default: Default list if value is None
        
    Returns:
        List or default
    """
    if default is None:
        default = []
    
    if value is None:
        return default
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    
    return default


def ensure_dict(value: Any, default: Dict = None) -> Dict:
    """
    Ensure value is a dict, return default if None.
    
    Args:
        value: Value to check
        default: Default dict if value is None
        
    Returns:
        Dict or default
    """
    if default is None:
        default = {}
    
    if value is None:
        return default
    if isinstance(value, dict):
        return value
    
    return default


def build_forecast_response(
    results: Dict[str, Any],
    data_maturity: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a stable forecast response from pipeline results.
    
    Handles all adaptive pipeline states safely:
    - EXCELLENT data: Full response
    - GOOD data: Full response with limited models
    - MEDIUM data: Partial response (prophet only)
    - POOR data: Minimal response
    - Partial failures: Graceful degradation
    
    Args:
        results: Raw results from ForecastingPipeline.run()
        data_maturity: Data maturity analysis results
        
    Returns:
        Stable, serialized response ready for API
    """
    # Extract core fields safely
    best_model = results.get("best_model")
    forecast = ensure_list(results.get("forecast"))
    metrics = ensure_dict(results.get("metrics"))
    model_comparison_raw = results.get("model_comparison")
    
    # Build model_comparison safely
    if model_comparison_raw and isinstance(model_comparison_raw, dict):
        model_comparison = {
            "models": ensure_list(model_comparison_raw.get("models")),
            "best_model": model_comparison_raw.get("best_model"),
            "metrics": ensure_dict(model_comparison_raw.get("metrics")),
            "feature_importance": model_comparison_raw.get("feature_importance"),
        }
    else:
        model_comparison = None
    
    # Extract risk fields safely
    risk_intelligence = results.get("risk_intelligence")
    anomalies = ensure_list(results.get("anomalies_detected"))
    volatility = results.get("volatility_analysis")
    trend = results.get("trend_analysis")
    recommendations = ensure_list(results.get("recommendations"))
    
    # Build response
    response = {
        "best_model": best_model,
        "forecast": forecast if forecast else None,
        "metrics": metrics if metrics else None,
        "model_comparison": model_comparison,
        "risk_level": results.get("risk_level"),
        "confidence_score": results.get("confidence_score"),
        "generated_at": datetime.utcnow(),
        
        # Data maturity
        "data_maturity": data_maturity.get("data_maturity"),
        "forecast_reliability_score": data_maturity.get("forecast_reliability_score"),
        "enabled_models": ensure_list(data_maturity.get("recommended_models")),
        "disabled_models": ensure_list(data_maturity.get("disabled_models")),
        
        # Risk intelligence
        "risk_score": results.get("risk_score"),
        "risk_intelligence": risk_intelligence,
        "anomalies_detected": anomalies,
        "volatility_analysis": volatility,
        "trend_analysis": trend,
        "recommendations": recommendations,
    }
    
    # Serialize all values
    return serialize_forecast_response(response)
