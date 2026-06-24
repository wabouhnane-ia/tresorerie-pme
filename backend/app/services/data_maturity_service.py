"""
Adaptive Data Maturity and Quality Service — Analyzes dataset and recommends models.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
import logging
from datetime import datetime

from app.services.historical_depth_service import HistoricalDepthService

logger = logging.getLogger(__name__)


class DataMaturityLevel:
    POOR = "POOR"
    MEDIUM = "MEDIUM"
    GOOD = "GOOD"
    EXCELLENT = "EXCELLENT"


class DataMaturityService:
    """
    Analyzes dataset quality and recommends appropriate forecasting models.
    """

    def __init__(self):
        self.required_columns = ["date", "treasury_balance"]
        self.historical_depth_service = HistoricalDepthService()

    def analyze_dataset(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Complete dataset analysis with historical depth validation.

        Args:
            df: Input DataFrame with financial data

        Returns:
            Data maturity analysis dictionary
        """
        logger.info("Starting data maturity analysis")

        # Basic validation
        validation = self._validate_dataset(df)
        if not validation["is_valid"]:
            return {
                "data_maturity": DataMaturityLevel.POOR,
                "validation_errors": validation["errors"],
                "is_valid": False,
                "recommended_models": [],
                "disabled_models": ["prophet", "lstm"],
                "confidence_level": "low",
                "forecast_reliability_score": 0,
                "historical_depth": self.historical_depth_service._get_insufficient_result("Invalid dataset"),
                "forecasting_enabled": False,
            }

        # === PHASE 1A: Historical Depth Analysis ===
        historical_depth = self.historical_depth_service.calculate_historical_depth(df)
        logger.info(f"Historical depth: {historical_depth['historical_months']} months, sufficient: {historical_depth['is_sufficient']}")

        # If insufficient historical depth, block forecasting but allow upload
        if not historical_depth["forecasting_enabled"]:
            logger.warning(f"Insufficient historical depth: {historical_depth['historical_months']} months < {self.historical_depth_service.MINIMUM_MONTHS} required")
            return {
                "data_maturity": DataMaturityLevel.POOR,
                "validation_errors": [],
                "is_valid": True,  # Upload is valid, just insufficient for forecasting
                "recommended_models": [],
                "disabled_models": ["prophet", "lstm"],
                "confidence_level": "insufficient_history",
                "forecast_reliability_score": 0,
                "historical_depth": historical_depth,
                "forecasting_enabled": False,
                "months_of_history": historical_depth["historical_months"],
                "onboarding_status": historical_depth["onboarding_status"],
                "onboarding_message": self.historical_depth_service.get_onboarding_message(historical_depth),
            }

        # Calculate metrics (existing logic)
        row_count = len(df)
        months_of_history = historical_depth["historical_months"]  # Use precise calculation
        missing_ratio = self._calculate_missing_ratio(df)
        frequency = self._detect_frequency(df)
        stability_score = self._calculate_stability_score(df)
        volatility_score = self._calculate_volatility_score(df)

        # Determine maturity level (enhanced with historical depth)
        maturity_level = self._determine_maturity_level(
            months_of_history,
            row_count,
            missing_ratio
        )

        # Recommend models
        recommended_models, disabled_models = self._recommend_models(
            maturity_level,
            months_of_history,
            row_count
        )

        # Calculate reliability score (enhanced with historical depth)
        reliability_score = self._calculate_reliability_score(
            months_of_history,
            row_count,
            missing_ratio,
            stability_score,
            volatility_score
        )

        confidence_level = self._determine_confidence_level(reliability_score)

        analysis = {
            "data_maturity": maturity_level,
            "months_of_history": months_of_history,
            "row_count": row_count,
            "missing_ratio": missing_ratio,
            "frequency": frequency,
            "stability_score": stability_score,
            "volatility_score": volatility_score,
            "recommended_models": recommended_models,
            "disabled_models": disabled_models,
            "confidence_level": confidence_level,
            "forecast_reliability_score": reliability_score,
            "is_valid": True,
            "historical_depth": historical_depth,
            "forecasting_enabled": True,  # Passed historical depth validation
            "onboarding_status": historical_depth["onboarding_status"],
            "onboarding_message": self.historical_depth_service.get_onboarding_message(historical_depth),
        }

        logger.info(f"Data maturity analysis completed: {maturity_level} with {months_of_history} months history")
        return analysis

    def _validate_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform basic dataset validation.

        Args:
            df: Input DataFrame

        Returns:
            Validation results
        """
        errors = []
        is_valid = True

        if df.empty:
            errors.append("DataFrame is empty")
            is_valid = False

        missing_columns = [col for col in self.required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
            is_valid = False

        if is_valid and len(df) < 10:
            errors.append("Too few data points (minimum 10 required)")
            is_valid = False

        if is_valid:
            try:
                pd.to_datetime(df["date"])
            except Exception as e:
                errors.append(f"Invalid date format: {e}")
                is_valid = False

        return {
            "is_valid": is_valid,
            "errors": errors,
        }

    def _calculate_months_of_history(self, df: pd.DataFrame) -> int:
        """
        Calculate number of months of historical data.

        Args:
            df: Input DataFrame

        Returns:
            Number of months
        """
        try:
            dates = pd.to_datetime(df["date"])
            date_range = dates.max() - dates.min()
            months = int(date_range.days / 30)
            return max(1, months)
        except Exception:
            return 1

    def _calculate_missing_ratio(self, df: pd.DataFrame) -> float:
        """
        Calculate ratio of missing values.

        Args:
            df: Input DataFrame

        Returns:
            Missing ratio (0.0 to 1.0)
        """
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        return round(missing_cells / total_cells if total_cells > 0 else 0.0, 4)

    def _detect_frequency(self, df: pd.DataFrame) -> str:
        """
        Detect data frequency (daily, weekly, monthly).

        Args:
            df: Input DataFrame

        Returns:
            Frequency string
        """
        try:
            dates = pd.to_datetime(df["date"]).sort_values()
            diffs = dates.diff().dropna()
            median_days = diffs.dt.days.median()

            if median_days <= 2:
                return "daily"
            elif median_days <= 10:
                return "weekly"
            else:
                return "monthly"
        except Exception:
            return "unknown"

    def _calculate_stability_score(self, df: pd.DataFrame) -> float:
        """
        Calculate temporal stability score (0-100).

        Args:
            df: Input DataFrame

        Returns:
            Stability score
        """
        try:
            if "treasury_balance" not in df.columns:
                return 50.0

            balances = df["treasury_balance"].dropna()
            if len(balances) < 2:
                return 50.0

            # Calculate coefficient of variation
            cv = balances.std() / (balances.mean() if balances.mean() != 0 else 1)
            stability = max(0.0, min(100.0, 100.0 - (cv * 100)))
            return round(stability, 2)
        except Exception:
            return 50.0

    def _calculate_volatility_score(self, df: pd.DataFrame) -> float:
        """
        Calculate volatility score (0-100, lower is better).

        Args:
            df: Input DataFrame

        Returns:
            Volatility score
        """
        try:
            if "treasury_balance" not in df.columns:
                return 50.0

            balances = df["treasury_balance"].dropna()
            if len(balances) < 2:
                return 50.0

            pct_changes = balances.pct_change().dropna().abs()
            volatility = pct_changes.mean() * 100
            return round(max(0.0, min(100.0, 100.0 - volatility)), 2)
        except Exception:
            return 50.0

    def _determine_maturity_level(
        self,
        months: int,
        rows: int,
        missing_ratio: float,
    ) -> str:
        """
        Determine data maturity level.

        Args:
            months: Number of months of history
            rows: Number of rows
            missing_ratio: Missing value ratio

        Returns:
            Maturity level string
        """
        if months < 3 or rows < 30 or missing_ratio > 0.2:
            return DataMaturityLevel.POOR
        elif 3 <= months < 6 or missing_ratio > 0.1:
            return DataMaturityLevel.MEDIUM
        elif 6 <= months < 12:
            return DataMaturityLevel.GOOD
        else:
            return DataMaturityLevel.EXCELLENT

    def _recommend_models(
        self,
        maturity_level: str,
        months: int,
        rows: int,
    ) -> Tuple[List[str], List[str]]:
        """
        Recommend appropriate models based on maturity.

        Args:
            maturity_level: Data maturity level
            months: Number of months of history
            rows: Number of rows

        Returns:
            Tuple of (recommended_models, disabled_models)
        """
        all_models = ["prophet", "lstm"]
        recommended = []
        disabled = []

        if maturity_level == DataMaturityLevel.POOR:
            disabled = all_models
        elif maturity_level == DataMaturityLevel.MEDIUM:
            recommended = ["prophet"]
            disabled = ["lstm"]
        elif maturity_level == DataMaturityLevel.GOOD:
            recommended = ["prophet", "lstm"]
            disabled = []
        elif maturity_level == DataMaturityLevel.EXCELLENT:
            recommended = ["prophet", "lstm"]
            disabled = []

        return recommended, disabled

    def _calculate_reliability_score(
        self,
        months: int,
        rows: int,
        missing_ratio: float,
        stability: float,
        volatility: float,
    ) -> int:
        """
        Calculate overall forecast reliability score (0-100).

        Args:
            months: Number of months of history
            rows: Number of rows
            missing_ratio: Missing value ratio
            stability: Stability score
            volatility: Volatility score

        Returns:
            Reliability score
        """
        # Score components
        months_score = min(100.0, months * 8.33)  # 12 months → 100
        rows_score = min(100.0, rows * 0.4)  # 250 rows → 100
        missing_score = max(0.0, 100.0 - (missing_ratio * 500))
        stability_score = stability
        volatility_score = volatility

        # Weighted average
        score = (
            months_score * 0.30 +
            rows_score * 0.20 +
            missing_score * 0.20 +
            stability_score * 0.15 +
            volatility_score * 0.15
        )

        return max(0, min(100, int(score)))

    def _determine_confidence_level(self, reliability_score: int) -> str:
        """
        Determine confidence level from reliability score.

        Args:
            reliability_score: Reliability score (0-100)

        Returns:
            Confidence level string
        """
        if reliability_score <= 30:
            return "low"
        elif reliability_score <= 60:
            return "medium"
        elif reliability_score <= 80:
            return "high"
        else:
            return "very_high"
