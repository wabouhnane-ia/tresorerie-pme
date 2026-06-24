"""
Pydantic schemas for forecasting API.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ForecastMetrics(BaseModel):
    """Forecast evaluation metrics."""
    model: Optional[str] = None
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    r2: Optional[float] = None


class ForecastPoint(BaseModel):
    """Single forecast point with date and predictions."""
    date: str
    prediction: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    yhat: Optional[float] = None
    yhat_lower: Optional[float] = None
    yhat_upper: Optional[float] = None


class ModelComparison(BaseModel):
    """Comparison of all forecasting models."""
    models: List[str] = Field(default_factory=list)
    best_model: Optional[str] = None
    metrics: Dict[str, ForecastMetrics] = Field(default_factory=dict)
    feature_importance: Optional[Any] = None


class RiskFactor(BaseModel):
    """Risk factor contributing to overall risk."""
    type: str
    severity: str
    score: float  # Changed from int to float (numpy.float64 compatibility)
    message: str


class AnomalyDetected(BaseModel):
    """Detected financial anomaly."""
    type: str
    severity: str
    score: Optional[float] = None
    date: Optional[str] = None  # Already string, pandas.Timestamp will be converted
    message: str


class VolatilityAnalysis(BaseModel):
    """Volatility analysis results."""
    volatility_level: str
    stability_score: float
    rolling_std_7: Optional[float] = None
    rolling_std_30: Optional[float] = None


class TrendAnalysis(BaseModel):
    """Trend analysis results."""
    trend_direction: str
    trend_severity: str
    trend_score: float  # Changed from int to float (numpy.float64 compatibility)
    slope: Optional[float] = None


class LiquidityAnalysis(BaseModel):
    """Liquidity analysis results."""
    liquidity_score: float  # Changed from int to float (numpy.float64 compatibility)
    liquidity_level: str
    latest_balance: Optional[float] = None


class RiskIntelligence(BaseModel):
    """Complete risk intelligence analysis."""
    risk_level: str
    risk_score: float  # Changed from int to float (numpy.float64 compatibility)
    confidence_level: str
    risk_factors: List[RiskFactor]
    anomalies_detected: List[AnomalyDetected]
    volatility_analysis: VolatilityAnalysis
    trend_analysis: TrendAnalysis
    liquidity_analysis: LiquidityAnalysis
    recommendations: List[str]


class ForecastResponse(BaseModel):
    """Complete forecast response for dashboard."""
    best_model: Optional[str] = None
    forecast: Optional[List[ForecastPoint]] = None
    metrics: Optional[ForecastMetrics] = None
    model_comparison: Optional[ModelComparison] = None
    risk_level: Optional[str] = None
    confidence_score: Optional[float] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Data maturity fields
    data_maturity: Optional[str] = None
    forecast_reliability_score: Optional[float] = None
    enabled_models: List[str] = Field(default_factory=list)
    disabled_models: List[str] = Field(default_factory=list)
    
    # Risk intelligence fields
    risk_score: Optional[float] = None
    risk_intelligence: Optional[RiskIntelligence] = None
    anomalies_detected: List[AnomalyDetected] = Field(default_factory=list)
    volatility_analysis: Optional[VolatilityAnalysis] = None
    trend_analysis: Optional[TrendAnalysis] = None
    recommendations: List[str] = Field(default_factory=list)


class TrainRequest(BaseModel):
    """Request schema for training forecast models."""
    horizon_days: int = 30


class PredictRequest(BaseModel):
    """Request schema for generating forecasts."""
    horizon_days: int = 30
    use_best_model: bool = True


class ModelsResponse(BaseModel):
    """Response with list of available models."""
    models: List[str]
    description: Dict[str, str]
