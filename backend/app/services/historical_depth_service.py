"""
Historical Depth Service — Calculate and validate historical treasury data depth.

This service determines if uploaded financial data meets minimum requirements
for treasury intelligence forecasting.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)


class OnboardingStatus:
    """Onboarding status constants."""
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    MINIMUM_READY = "MINIMUM_READY"
    ADVANCED_READY = "ADVANCED_READY"


class HistoricalDepthService:
    """
    Service for calculating and validating historical depth of financial data.
    """

    # Business rules for minimum historical requirements with tolerance
    MINIMUM_MONTHS = settings.MIN_HISTORY_MONTHS
    RECOMMENDED_MONTHS = settings.ADVANCED_HISTORY_MONTHS
    OPTIMAL_MONTHS = settings.EXCELLENT_HISTORY_MONTHS
    TOLERANCE = settings.HISTORY_TOLERANCE

    def __init__(self):
        self.required_columns = ["date"]

    def calculate_historical_depth(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate comprehensive historical depth metrics.

        Args:
            df: Input DataFrame with financial data

        Returns:
            Dictionary with historical depth analysis
        """
        logger.info("Calculating historical depth")

        try:
            # Basic validation
            if df.empty or "date" not in df.columns:
                return self._get_insufficient_result("No date data available")

            # Convert dates and sort
            dates = pd.to_datetime(df["date"], errors='coerce')
            dates = dates.dropna().sort_values()
            
            if len(dates) < 2:
                return self._get_insufficient_result("Insufficient date records")

            # Calculate date range
            start_date = dates.min()
            end_date = dates.max()
            date_range = end_date - start_date

            # Calculate months of history with high precision (float)
            # This allows us to account for partial months and apply tolerance
            years = (end_date.year - start_date.year)
            months = (end_date.month - start_date.month)
            days = end_date.day - start_date.day
            
            # Total months as float
            historical_months = years * 12 + months + days / 30.44
            
            # Ensure minimum of 1 month
            historical_months = max(1.0, historical_months)

            # Calculate continuity quality (percentage of expected days with data)
            expected_days = date_range.days + 1
            actual_days = len(dates.unique())
            continuity_quality = round((actual_days / expected_days) * 100, 2) if expected_days > 0 else 0

            # Determine if sufficient for forecasting with tolerance
            is_sufficient = historical_months >= (self.MINIMUM_MONTHS - self.TOLERANCE)

            # Determine onboarding status (use tolerance for all thresholds)
            onboarding_status = self._determine_onboarding_status(historical_months)

            result = {
                "historical_months": historical_months,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "date_range_days": date_range.days,
                "continuity_quality": continuity_quality,
                "is_sufficient": is_sufficient,
                "onboarding_status": onboarding_status,
                "forecasting_enabled": is_sufficient,
                "months_needed": max(0, self.MINIMUM_MONTHS - historical_months),
                "recommendation_level": self._get_recommendation_level(historical_months),
            }

            logger.info(f"Historical depth calculated: {historical_months} months, sufficient: {is_sufficient}")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate historical depth: {e}")
            return self._get_insufficient_result(f"Calculation error: {str(e)}")

    def _determine_onboarding_status(self, months: float) -> str:
        """
        Determine onboarding status based on historical months with tolerance.

        Args:
            months: Number of historical months (float)

        Returns:
            Onboarding status string
        """
        if months < (self.MINIMUM_MONTHS - self.TOLERANCE):
            return OnboardingStatus.INSUFFICIENT_HISTORY
        elif months < (self.RECOMMENDED_MONTHS - self.TOLERANCE):
            return OnboardingStatus.MINIMUM_READY
        else:
            return OnboardingStatus.ADVANCED_READY

    def _get_recommendation_level(self, months: float) -> str:
        """
        Get recommendation level based on historical depth with tolerance.

        Args:
            months: Number of historical months (float)

        Returns:
            Recommendation level string
        """
        if months < (self.MINIMUM_MONTHS - self.TOLERANCE):
            return "insufficient"
        elif months < (self.RECOMMENDED_MONTHS - self.TOLERANCE):
            return "minimum"
        elif months < (self.OPTIMAL_MONTHS - self.TOLERANCE):
            return "recommended"
        else:
            return "optimal"

    def _get_insufficient_result(self, reason: str) -> Dict[str, Any]:
        """
        Get result for insufficient historical data.

        Args:
            reason: Reason for insufficiency

        Returns:
            Insufficient result dictionary
        """
        return {
            "historical_months": 0,
            "start_date": None,
            "end_date": None,
            "date_range_days": 0,
            "continuity_quality": 0,
            "is_sufficient": False,
            "onboarding_status": OnboardingStatus.INSUFFICIENT_HISTORY,
            "forecasting_enabled": False,
            "months_needed": self.MINIMUM_MONTHS,
            "recommendation_level": "insufficient",
            "error": reason,
        }

    def get_onboarding_message(self, depth_result: Dict[str, Any], locale: str = "fr") -> Dict[str, str]:
        """
        Get user-friendly onboarding messages based on depth analysis.

        Args:
            depth_result: Result from calculate_historical_depth

        Returns:
            Dictionary with title and message
        """
        status = depth_result.get("onboarding_status")
        months = depth_result.get("historical_months", 0)
        months_needed = depth_result.get("months_needed", 0)
        messages = {
            "fr": {
                OnboardingStatus.INSUFFICIENT_HISTORY: {
                    "title": "Données historiques supplémentaires requises",
                    "message": f"Vous avez {months} mois de données. L'intelligence trésorerie requiert au minimum {self.MINIMUM_MONTHS} mois pour activer les prévisions. Importez encore {months_needed} mois de données historiques.",
                },
                OnboardingStatus.MINIMUM_READY: {
                    "title": "Intelligence trésorerie activée",
                    "message": f"Avec {months} mois de données historiques, les prévisions de trésorerie sont disponibles. Pour plus de précision, vous pouvez importer jusqu'à {self.RECOMMENDED_MONTHS} mois de données.",
                },
                OnboardingStatus.ADVANCED_READY: {
                    "title": "Intelligence trésorerie avancée disponible",
                    "message": f"Avec {months} mois de données historiques, vous accédez aux capacités avancées de détection de saisonnalité et de scoring de confiance.",
                },
            },
            "en": {
                OnboardingStatus.INSUFFICIENT_HISTORY: {
                    "title": "Additional historical data required",
                    "message": f"You have {months} months of data. Treasury intelligence requires at least {self.MINIMUM_MONTHS} months to activate forecasting. Please upload {months_needed} more months of historical data.",
                },
                OnboardingStatus.MINIMUM_READY: {
                    "title": "Treasury intelligence activated",
                    "message": f"With {months} months of historical data, treasury forecasting is now available. For better accuracy, consider uploading up to {self.RECOMMENDED_MONTHS} months of data.",
                },
                OnboardingStatus.ADVANCED_READY: {
                    "title": "Advanced treasury intelligence available",
                    "message": f"With {months} months of historical data, advanced seasonality detection and confidence scoring are available.",
                },
            },
            "ar": {
                OnboardingStatus.INSUFFICIENT_HISTORY: {
                    "title": "مطلوب بيانات تاريخية إضافية",
                    "message": f"لديك {months} شهر من البيانات. يتطلب ذكاء الخزينة {self.MINIMUM_MONTHS} شهر على الأقل لتفعيل التوقعات. يرجى رفع {months_needed} شهر إضافي من البيانات التاريخية.",
                },
                OnboardingStatus.MINIMUM_READY: {
                    "title": "تم تفعيل ذكاء الخزينة",
                    "message": f"مع {months} شهر من البيانات التاريخية، أصبحت توقعات الخزينة متاحة. لتحسين الدقة، يمكنك رفع ما يصل إلى {self.RECOMMENDED_MONTHS} شهر من البيانات.",
                },
                OnboardingStatus.ADVANCED_READY: {
                    "title": "ذكاء الخزينة المتقدم متاح",
                    "message": f"مع {months} شهر من البيانات التاريخية، تتوفر قدرات متقدمة لاكتشاف الموسمية واحتساب الثقة.",
                },
            },
        }
        loc_messages = messages.get(locale, messages["fr"])

        if status == OnboardingStatus.INSUFFICIENT_HISTORY:
            return {**loc_messages[OnboardingStatus.INSUFFICIENT_HISTORY], "type": "warning"}
        elif status == OnboardingStatus.MINIMUM_READY:
            return {**loc_messages[OnboardingStatus.MINIMUM_READY], "type": "success"}
        else:  # ADVANCED_READY
            return {**loc_messages[OnboardingStatus.ADVANCED_READY], "type": "success"}

    def validate_forecasting_eligibility(self, company_id: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate if company is eligible for forecasting based on historical depth.

        Args:
            company_id: Company identifier
            df: Financial data DataFrame

        Returns:
            Validation result with eligibility status
        """
        depth_result = self.calculate_historical_depth(df)
        
        return {
            "company_id": company_id,
            "eligible": depth_result["forecasting_enabled"],
            "reason": "sufficient_history" if depth_result["forecasting_enabled"] else "insufficient_history",
            "historical_months": depth_result["historical_months"],
            "minimum_required": self.MINIMUM_MONTHS,
            "onboarding_status": depth_result["onboarding_status"],
            "message": self.get_onboarding_message(depth_result),
        }
