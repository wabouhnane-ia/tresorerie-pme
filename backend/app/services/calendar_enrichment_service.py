"""
Calendar Enrichment Service.
Generates deterministic calendar features for forecasting.
"""
import pandas as pd
from datetime import datetime
import holidays
from hijri_converter import Gregorian


class CalendarEnrichmentService:
    """Service for enriching data with calendar features."""

    def __init__(self, country_code: str = "MA"):
        """
        Initialize calendar service.
        
        Args:
            country_code: Country code for holiday detection (default: Morocco)
        """
        self.country_code = country_code
        self.holidays = holidays.CountryHoliday(country_code)

    def _is_ramadan(self, date: datetime) -> bool:
        """
        Check if a given date falls within Ramadan.
        
        Args:
            date: Gregorian date to check
        
        Returns:
            True if date is in Ramadan, False otherwise
        """
        try:
            hijri_date = Gregorian(date.year, date.month, date.day).to_hijri()
            # Ramadan is the 9th month of the Hijri calendar
            return hijri_date.month == 9
        except Exception:
            return False

    def enrich_calendar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enriches a DataFrame with calendar features.
        
        Args:
            df: DataFrame with a 'date' column
        
        Returns:
            DataFrame with added calendar features
        """
        df = df.copy()
        
        # Ensure date is datetime
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        
        # Basic calendar features
        df["weekday"] = df["date"].dt.weekday
        df["month"] = df["date"].dt.month
        df["quarter"] = df["date"].dt.quarter
        
        # Boolean flags
        df["is_weekend"] = df["date"].dt.dayofweek.isin([5, 6]).astype(int)
        df["is_month_start"] = df["date"].dt.is_month_start.astype(int)
        df["is_month_end"] = df["date"].dt.is_month_end.astype(int)
        df["is_quarter_start"] = df["date"].dt.is_quarter_start.astype(int)
        df["is_quarter_end"] = df["date"].dt.is_quarter_end.astype(int)
        
        # Business day (non-weekend and non-holiday)
        df["is_holiday"] = df["date"].isin(self.holidays).astype(int)
        df["is_business_day"] = ((df["is_weekend"] == 0) & (df["is_holiday"] == 0)).astype(int)
        
        # Ramadan detection
        df["is_ramadan"] = df["date"].apply(self._is_ramadan).astype(int)
        
        return df

    def get_calendar_features_for_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Generate calendar features for a specific date range.
        
        Args:
            start_date: Start date of the range
            end_date: End date of the range
        
        Returns:
            DataFrame with calendar features for each date in the range
        """
        dates = pd.date_range(start=start_date, end=end_date)
        df = pd.DataFrame({"date": dates})
        return self.enrich_calendar_features(df)
