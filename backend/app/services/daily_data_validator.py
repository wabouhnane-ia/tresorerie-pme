"""
Daily Data Enforcement Service

PLATFORM STANDARD: 1 row = 1 day
Treasury forecasting requires DAILY treasury data.
Monthly aggregated files must NOT be accepted.

This service:
1. Detects dataset frequency (DAILY, MONTHLY, QUARTERLY, YEARLY)
2. Validates daily density and coverage
3. Rejects non-daily aggregated datasets
4. Provides clear business messages for rejection reasons
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from enum import Enum
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DatasetFrequency(str, Enum):
    """Dataset frequency classification"""
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
    UNKNOWN = "UNKNOWN"


class DailyDataValidationResult:
    """Result of daily data validation"""
    
    def __init__(
        self,
        is_valid: bool,
        frequency: DatasetFrequency,
        total_rows: int,
        date_range_days: int,
        observed_days: int,
        coverage_rate: float,
        business_messages: List[str],
        technical_details: Dict[str, Any]
    ):
        self.is_valid = is_valid
        self.frequency = frequency
        self.total_rows = total_rows
        self.date_range_days = date_range_days
        self.observed_days = observed_days
        self.coverage_rate = coverage_rate
        self.business_messages = business_messages
        self.technical_details = technical_details
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "is_valid": self.is_valid,
            "frequency": self.frequency.value,
            "total_rows": self.total_rows,
            "date_range_days": self.date_range_days,
            "observed_days": self.observed_days,
            "coverage_rate": self.coverage_rate,
            "business_messages": self.business_messages,
            "technical_details": self.technical_details
        }


class DailyDataValidator:
    """
    Validates that uploaded datasets contain daily treasury data.
    
    Business Rules:
    - Accept: Daily observations with >= 80% coverage
    - Reject: Monthly, quarterly, or yearly aggregated data
    - Reject: Daily data with < 80% coverage (too sparse)
    """
    
    # Validation thresholds
    MINIMUM_COVERAGE_RATE = 0.80  # 80% daily coverage required
    MINIMUM_HISTORICAL_DAYS = 730  # 24 months in days
    
    # Date format patterns for detection
    MONTHLY_PATTERNS = [
        r'^\d{4}-\d{2}$',           # 2024-01
        r'^\d{2}/\d{4}$',           # 01/2024
        r'^\d{4}/\d{2}$',           # 2024/01
        r'^[A-Za-z]{3,9}\s+\d{4}$', # January 2024
    ]
    
    QUARTERLY_PATTERNS = [
        r'^Q[1-4]-\d{4}$',          # Q1-2024
        r'^\d{4}-Q[1-4]$',          # 2024-Q1
        r'^[1-4]Q\d{4}$',           # 1Q2024
    ]
    
    YEARLY_PATTERNS = [
        r'^\d{4}$',                 # 2024
    ]
    
    def __init__(self):
        """Initialize daily data validator"""
        pass
    
    def validate_daily_data(self, df: pd.DataFrame, skip_historical_depth_check: bool = False) -> DailyDataValidationResult:
        """
        Main validation entry point.
        
        Args:
            df: DataFrame with 'date' column
            skip_historical_depth_check: If True, skip checking historical depth (use for incremental uploads)
            
        Returns:
            DailyDataValidationResult with validation outcome
        """
        try:
            # Ensure date column exists
            if 'date' not in df.columns:
                return self._create_error_result(
                    "Missing 'date' column in dataset"
                )
            
            # Ensure date column is datetime
            df_copy = df.copy()
            df_copy['date'] = pd.to_datetime(df_copy['date'], errors='coerce')
            
            # Remove invalid dates
            df_copy = df_copy.dropna(subset=['date'])
            
            if len(df_copy) == 0:
                return self._create_error_result(
                    "No valid dates found in dataset"
                )
            
            # Step 1: Detect dataset frequency
            frequency = self._detect_frequency(df_copy)
            
            # Step 2: Reject non-daily frequencies immediately
            if frequency != DatasetFrequency.DAILY:
                return self._create_rejection_result(frequency, df_copy)
            
            # Step 3: Validate daily density and coverage
            coverage_result = self._validate_daily_coverage(df_copy)
            
            # Step 4: Check minimum historical requirement (only if not skipped)
            historical_check = self._validate_historical_depth(df_copy) if not skip_historical_depth_check else {
                "days": 0,
                "months": 0.0,
                "meets_minimum": True
            }
            
            # Combine results
            is_valid = (
                coverage_result["meets_coverage"] and 
                historical_check["meets_minimum"]
            )
            
            business_messages = []
            
            if not coverage_result["meets_coverage"]:
                business_messages.append(
                    f"Daily coverage is {coverage_result['coverage_rate']:.1%}. "
                    f"Minimum required: {self.MINIMUM_COVERAGE_RATE:.0%}. "
                    f"Please provide more complete daily treasury data."
                )
            
            if not skip_historical_depth_check and not historical_check["meets_minimum"]:
                business_messages.append(
                    f"Historical depth: {historical_check['months']:.1f} months. "
                    f"Minimum required: {self.MINIMUM_HISTORICAL_DAYS / 30.44:.0f} months. "
                    f"Please provide at least 24 months of daily treasury history."
                )
            
            if is_valid:
                history_part = f", History: {historical_check['months']:.1f} months" if not skip_historical_depth_check else ""
                business_messages.append(
                    f"Daily treasury data validated successfully. "
                    f"Coverage: {coverage_result['coverage_rate']:.1%}{history_part}."
                )
            
            return DailyDataValidationResult(
                is_valid=is_valid,
                frequency=DatasetFrequency.DAILY,
                total_rows=len(df_copy),
                date_range_days=coverage_result["expected_days"],
                observed_days=coverage_result["observed_days"],
                coverage_rate=coverage_result["coverage_rate"],
                business_messages=business_messages,
                technical_details={
                    "earliest_date": df_copy['date'].min().isoformat(),
                    "latest_date": df_copy['date'].max().isoformat(),
                    "missing_days": coverage_result["missing_days"],
                    "historical_months": historical_check["months"],
                    "meets_coverage": coverage_result["meets_coverage"],
                    "meets_historical_depth": historical_check["meets_minimum"]
                }
            )
            
        except Exception as e:
            logger.error(f"Daily data validation failed: {e}")
            return self._create_error_result(f"Validation error: {str(e)}")
    
    def _detect_frequency(self, df: pd.DataFrame) -> DatasetFrequency:
        """
        Detect dataset frequency by analyzing date patterns and intervals.
        
        Args:
            df: DataFrame with datetime 'date' column
            
        Returns:
            Detected frequency
        """
        try:
            # Sort by date
            df_sorted = df.sort_values('date').reset_index(drop=True)
            dates = df_sorted['date']
            
            if len(dates) < 2:
                return DatasetFrequency.UNKNOWN
            
            # Calculate intervals between consecutive dates
            intervals = dates.diff().dropna()
            
            # Get median interval in days
            median_interval_days = intervals.dt.days.median()
            
            # Get date range span
            date_span_days = (dates.max() - dates.min()).days
            
            # Calculate expected rows for different frequencies
            expected_daily = date_span_days
            expected_monthly = date_span_days / 30.44
            expected_quarterly = date_span_days / 91.31
            expected_yearly = date_span_days / 365.25
            
            actual_rows = len(dates)
            
            # Frequency detection logic
            # Daily: median interval ~1 day, row count close to date span
            if median_interval_days <= 7 and actual_rows >= expected_daily * 0.5:
                return DatasetFrequency.DAILY
            
            # Monthly: median interval ~30 days, row count close to months
            elif 20 <= median_interval_days <= 40 and abs(actual_rows - expected_monthly) < expected_monthly * 0.3:
                return DatasetFrequency.MONTHLY
            
            # Quarterly: median interval ~90 days
            elif 70 <= median_interval_days <= 110 and abs(actual_rows - expected_quarterly) < expected_quarterly * 0.5:
                return DatasetFrequency.QUARTERLY
            
            # Yearly: median interval ~365 days
            elif median_interval_days >= 300:
                return DatasetFrequency.YEARLY
            
            # Check if dates look like month-end or month-start patterns (monthly indicator)
            if self._is_monthly_pattern(dates):
                return DatasetFrequency.MONTHLY
            
            # Default to DAILY if intervals are small but sparse
            if median_interval_days <= 10:
                return DatasetFrequency.DAILY
            
            return DatasetFrequency.UNKNOWN
            
        except Exception as e:
            logger.error(f"Frequency detection failed: {e}")
            return DatasetFrequency.UNKNOWN
    
    def _is_monthly_pattern(self, dates: pd.Series) -> bool:
        """
        Check if dates follow a monthly pattern (month-end or month-start).
        
        Args:
            dates: Series of datetime dates
            
        Returns:
            True if monthly pattern detected
        """
        try:
            # Check if most dates are at month boundaries
            month_starts = (dates.dt.day == 1).sum()
            month_ends = (dates.dt.day >= 28).sum()  # 28-31 considered month-end
            
            total = len(dates)
            
            # If >70% of dates are at month boundaries, likely monthly
            return (month_starts / total > 0.7) or (month_ends / total > 0.7)
            
        except Exception:
            return False
    
    def _validate_daily_coverage(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate daily density and coverage rate.
        
        Args:
            df: DataFrame with datetime 'date' column
            
        Returns:
            Dictionary with coverage analysis
        """
        try:
            dates = df['date'].sort_values()
            earliest = dates.min()
            latest = dates.max()
            
            # Calculate expected days (inclusive)
            expected_days = (latest - earliest).days + 1
            
            # Count unique observed days
            observed_days = dates.nunique()
            
            # Calculate coverage rate
            coverage_rate = observed_days / expected_days if expected_days > 0 else 0
            
            # Calculate missing days
            missing_days = expected_days - observed_days
            
            # Check if meets minimum coverage
            meets_coverage = coverage_rate >= self.MINIMUM_COVERAGE_RATE
            
            return {
                "expected_days": expected_days,
                "observed_days": observed_days,
                "missing_days": missing_days,
                "coverage_rate": coverage_rate,
                "meets_coverage": meets_coverage
            }
            
        except Exception as e:
            logger.error(f"Coverage validation failed: {e}")
            return {
                "expected_days": 0,
                "observed_days": 0,
                "missing_days": 0,
                "coverage_rate": 0.0,
                "meets_coverage": False
            }
    
    def _validate_historical_depth(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate historical depth requirement.
        
        Args:
            df: DataFrame with datetime 'date' column
            
        Returns:
            Dictionary with historical depth analysis
        """
        try:
            dates = df['date']
            earliest = dates.min()
            latest = dates.max()
            
            # Calculate historical span
            historical_days = (latest - earliest).days + 1
            historical_months = historical_days / 30.44
            
            # Check if meets minimum
            meets_minimum = historical_days >= self.MINIMUM_HISTORICAL_DAYS
            
            return {
                "days": historical_days,
                "months": historical_months,
                "meets_minimum": meets_minimum
            }
            
        except Exception as e:
            logger.error(f"Historical depth validation failed: {e}")
            return {
                "days": 0,
                "months": 0.0,
                "meets_minimum": False
            }
    
    def _create_rejection_result(
        self, 
        frequency: DatasetFrequency, 
        df: pd.DataFrame
    ) -> DailyDataValidationResult:
        """
        Create rejection result for non-daily data.
        
        Args:
            frequency: Detected frequency
            df: DataFrame
            
        Returns:
            Rejection result with business message
        """
        business_messages = []
        
        if frequency == DatasetFrequency.MONTHLY:
            business_messages.append(
                "Monthly aggregated data detected. "
                "The platform requires daily treasury transactions. "
                "Please export daily treasury movements from your ERP/accounting system."
            )
        elif frequency == DatasetFrequency.QUARTERLY:
            business_messages.append(
                "Quarterly aggregated data detected. "
                "The platform requires daily treasury transactions. "
                "Please export daily treasury movements from your ERP/accounting system."
            )
        elif frequency == DatasetFrequency.YEARLY:
            business_messages.append(
                "Yearly aggregated data detected. "
                "The platform requires daily treasury transactions. "
                "Please export daily treasury movements from your ERP/accounting system."
            )
        else:
            business_messages.append(
                "Unable to determine data frequency. "
                "The platform requires daily treasury transactions. "
                "Please ensure your file contains daily treasury movements."
            )
        
        dates = df['date']
        
        return DailyDataValidationResult(
            is_valid=False,
            frequency=frequency,
            total_rows=len(df),
            date_range_days=(dates.max() - dates.min()).days + 1,
            observed_days=dates.nunique(),
            coverage_rate=0.0,
            business_messages=business_messages,
            technical_details={
                "earliest_date": dates.min().isoformat(),
                "latest_date": dates.max().isoformat(),
                "detected_frequency": frequency.value,
                "rejection_reason": "non_daily_frequency"
            }
        )
    
    def _create_error_result(self, error_message: str) -> DailyDataValidationResult:
        """
        Create error result for validation failures.
        
        Args:
            error_message: Error description
            
        Returns:
            Error result
        """
        return DailyDataValidationResult(
            is_valid=False,
            frequency=DatasetFrequency.UNKNOWN,
            total_rows=0,
            date_range_days=0,
            observed_days=0,
            coverage_rate=0.0,
            business_messages=[error_message],
            technical_details={"error": error_message}
        )
