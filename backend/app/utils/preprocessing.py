"""
Data preprocessing utilities for time series forecasting.
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, Dict, Any


class TimeSeriesPreprocessor:
    """
    Preprocessor for time series data with feature engineering and scaling.
    """

    def __init__(self, target_column: str = "treasury_balance"):
        self.target_column = target_column
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.feature_columns = []
        self.is_fitted = False

    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create temporal features from date column.

        Args:
            df: Input DataFrame with 'date' column

        Returns:
            DataFrame with time features added
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["day"] = df["date"].dt.day
        df["month"] = df["date"].dt.month
        df["year"] = df["date"].dt.year
        df["quarter"] = df["date"].dt.quarter
        df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
        df["day_of_week"] = df["date"].dt.dayofweek
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        return df

    def create_lag_features(self, df: pd.DataFrame, lags: list = None) -> pd.DataFrame:
        """
        Create lag features for target column.

        Args:
            df: Input DataFrame
            lags: List of lag periods (days)

        Returns:
            DataFrame with lag features
        """
        if lags is None:
            lags = [1, 7, 30]

        df = df.copy()
        for lag in lags:
            df[f"lag_{lag}"] = df[self.target_column].shift(lag)
        return df

    def create_rolling_features(self, df: pd.DataFrame, windows: list = None) -> pd.DataFrame:
        """
        Create rolling mean and std features.

        Args:
            df: Input DataFrame
            windows: List of rolling window sizes

        Returns:
            DataFrame with rolling features
        """
        if windows is None:
            windows = [7, 30]

        df = df.copy()
        for window in windows:
            df[f"rolling_mean_{window}"] = df[self.target_column].rolling(window=window).mean()
            df[f"rolling_std_{window}"] = df[self.target_column].rolling(window=window).std()
        return df

    def create_business_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create business-specific features.

        Args:
            df: Input DataFrame with cash_inflow, cash_outflow, net_cashflow

        Returns:
            DataFrame with business features
        """
        df = df.copy()

        if "cash_inflow" in df.columns and "cash_outflow" in df.columns:
            df["inflow_outflow_ratio"] = df["cash_inflow"] / df["cash_outflow"].replace(0, 1)

        if "treasury_balance" in df.columns:
            df["negative_balance_flag"] = (df["treasury_balance"] < 0).astype(int)

        return df

    def fit_transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Fit the scaler and transform the data.

        Args:
            df: Input DataFrame

        Returns:
            Tuple of (transformed DataFrame, metadata dict)
        """
        df = self.create_time_features(df)
        df = self.create_lag_features(df)
        df = self.create_rolling_features(df)
        df = self.create_business_features(df)

        df = df.dropna().reset_index(drop=True)

        excluded_columns = [
            "_id",
            "company_id",
            "created_at",
            "updated_at",
            "date",
            "upload_id",
            "uploaded_at"
        ]

        self.feature_columns = [
            col
            for col in df.columns
            if col not in excluded_columns
            and col != self.target_column
            and pd.api.types.is_numeric_dtype(df[col])
        ]

        numeric_columns = self.feature_columns + [self.target_column]

        scaled_data = self.scaler.fit_transform(df[numeric_columns])
        df_scaled = pd.DataFrame(scaled_data, columns=numeric_columns, index=df.index)

        self.is_fitted = True

        metadata = {
            "feature_columns": self.feature_columns,
            "target_column": self.target_column,
            "scaler": self.scaler,
        }

        return df_scaled, metadata

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform new data using the fitted scaler.

        Args:
            df: Input DataFrame

        Returns:
            Transformed DataFrame
        """
        if not self.is_fitted:
            raise ValueError("Preprocessor has not been fitted yet. Call fit_transform first.")

        df = self.create_time_features(df)
        df = self.create_lag_features(df)
        df = self.create_rolling_features(df)
        df = self.create_business_features(df)

        df = df.dropna().reset_index(drop=True)

        numeric_columns = self.feature_columns + [self.target_column]

        scaled_data = self.scaler.transform(df[numeric_columns])
        df_scaled = pd.DataFrame(scaled_data, columns=numeric_columns, index=df.index)

        return df_scaled

    def inverse_transform(self, scaled_values: np.ndarray) -> np.ndarray:
        """
        Inverse transform scaled values back to original scale.

        Args:
            scaled_values: Scaled values to inverse transform

        Returns:
            Values in original scale
        """
        if not self.is_fitted:
            raise ValueError("Preprocessor has not been fitted yet.")

        dummy = np.zeros((len(scaled_values), len(self.feature_columns) + 1))
        dummy[:, -1] = scaled_values.flatten()
        return self.scaler.inverse_transform(dummy)[:, -1]


def create_sequences(
    data: np.ndarray,
    target_idx: int,
    sequence_length: int = 30
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create sequences for LSTM model.

    Args:
        data: Input data array
        target_idx: Index of target column
        sequence_length: Length of each sequence

    Returns:
        Tuple of (X, y) arrays
    """
    X, y = [], []
    for i in range(sequence_length, len(data)):
        X.append(data[i - sequence_length:i, :])
        y.append(data[i, target_idx])
    return np.array(X), np.array(y)
