"""
LSTM Data Preparation Module.
IMPORTANT: NO DATA LEAKAGE!
- Split train/test BEFORE any scaling
- Scaler is fit ONLY on training data
"""

import numpy as np
import pandas as pd

from sklearn.preprocessing import RobustScaler  # CORRECTION : résiste aux 43 outliers net_cashflow (jour 28/mois)


class LSTMDataPreparation:

    def __init__(
        self,
        sequence_length=30
    ):
        """
        Initialize LSTM data preparer.
        
        Args:
            sequence_length: Number of past days to use for prediction
        """
        self.sequence_length = sequence_length
        
        self.scaler = RobustScaler()  # CORRECTION : résiste aux 43 outliers net_cashflow (jour 28/mois)

        self.features = [
            "treasury_balance",  # CORRECTION : index 0 = cible (ne pas changer)
            "tb_lag_1",  # CORRECTION : corr=0.990 avec cible
            "tb_lag_7",  # CORRECTION : corr=0.946 avec cible
            "tb_lag_30",  # CORRECTION : corr=0.936 avec cible
            "tb_rolling_7",  # CORRECTION : corr=0.984 avec cible
            "tb_rolling_30",  # CORRECTION : corr=0.955 avec cible
            "tb_rolling_std_7",
            "tb_rolling_std_30",
            "treasury_growth",
            "inflow_outflow_ratio",
            "expected_net_cashflow",
            "day_sin",
            "day_cos",
            "month_sin",
            "month_cos",
            "weekday_sin",
            "weekday_cos",
            "cash_inflow",
            "cash_outflow",
            "net_cashflow",
            "scheduled_receipts",
            "overdue_receipts",
            "scheduled_payments",
            "overdue_payments",
            "is_payment_day",  # CORRECTION : flag outliers récurrents (jour 28 et jour 1)
            # liquidity_stress_score SUPPRIMÉ : toujours 0
            # number_of_clients SUPPRIMÉ : toujours 0
        ]

    def add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        CORRECTION : ajoute lags et rolling manquants.
        lag_1 corr=0.990, rolling_7 corr=0.984 avec treasury_balance.
        Sans ces features, LSTM fait pire que copie de la veille.
        """
        df = df.copy()
        
        # CORRECTION : gérer date en datetime ou string
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        
        df = df.sort_values("date").reset_index(drop=True) if "date" in df.columns else df.reset_index(drop=True)

        # Lags treasury_balance
        df["tb_lag_1"] = df["treasury_balance"].shift(1)  # CORRECTION : corr=0.990 avec cible
        df["tb_lag_7"] = df["treasury_balance"].shift(7)  # CORRECTION : corr=0.946 avec cible
        df["tb_lag_30"] = df["treasury_balance"].shift(30)  # CORRECTION : corr=0.936 avec cible

        # Rolling means
        df["tb_rolling_7"] = df["treasury_balance"].rolling(7).mean()  # CORRECTION : corr=0.984 avec cible
        df["tb_rolling_30"] = df["treasury_balance"].rolling(30).mean()  # CORRECTION : corr=0.955 avec cible

        # Rolling standard deviations
        df["tb_rolling_std_7"] = df["treasury_balance"].rolling(7).std()
        df["tb_rolling_std_30"] = df["treasury_balance"].rolling(30).std()

        # Treasury growth
        df["treasury_growth"] = df["treasury_balance"].pct_change().fillna(0)

        # Inflow/outflow ratio
        df["inflow_outflow_ratio"] = (df["cash_inflow"] / (df["cash_outflow"] + 1e-9)).fillna(0)

        # Expected net cashflow from commitments
        df["expected_net_cashflow"] = df["scheduled_receipts"] - df["scheduled_payments"]

        # Ensure commitment columns are present (fill with 0 if not)
        for col in ["scheduled_receipts", "overdue_receipts", "scheduled_payments", "overdue_payments"]:
            if col not in df.columns:
                df[col] = 0.0
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        # Cyclic calendar features
        if "date" in df.columns:
            dates = pd.to_datetime(df["date"])
            df["day_sin"] = np.sin(2 * np.pi * dates.dt.day / 31.0)
            df["day_cos"] = np.cos(2 * np.pi * dates.dt.day / 31.0)
            df["month_sin"] = np.sin(2 * np.pi * dates.dt.month / 12.0)
            df["month_cos"] = np.cos(2 * np.pi * dates.dt.month / 12.0)
            df["weekday_sin"] = np.sin(2 * np.pi * dates.dt.dayofweek / 7.0)
            df["weekday_cos"] = np.cos(2 * np.pi * dates.dt.dayofweek / 7.0)
        else:
            df["day_sin"] = 0.0
            df["day_cos"] = 0.0
            df["month_sin"] = 0.0
            df["month_cos"] = 0.0
            df["weekday_sin"] = 0.0
            df["weekday_cos"] = 0.0

        # Replace NaN from rolling std
        df["tb_rolling_std_7"] = df["tb_rolling_std_7"].fillna(0.0)
        df["tb_rolling_std_30"] = df["tb_rolling_std_30"].fillna(0.0)

        # Flag paiements récurrents
        # CORRECTION : capture les 43 outliers (jour 28 et jour 1 de chaque mois)
        if "date" in df.columns:
            df["is_payment_day"] = (
                (pd.to_datetime(df["date"]).dt.day == 28) |
                (pd.to_datetime(df["date"]).dt.day == 1)
            ).astype(float)
        else:
            df["is_payment_day"] = 0.0

        # Supprimer NaN créés par lags/rolling
        df = df.dropna().reset_index(drop=True)  # CORRECTION : supprime NaN des shift/rolling

        return df

    def get_feature_metadata(self, df: pd.DataFrame) -> dict:
        """
        Get metadata about features for persistence.
        """
        feature_list = self.features.copy()
        
        return {
            "feature_version": "2.0",
            "feature_count": len(feature_list),
            "generated_features": feature_list,
            "dataset_quality": {
                "rows": len(df),
                "missing_values": df.isnull().sum().to_dict()
            }
        }

    def select_features(self, df):
        """Select only the features we need for modeling."""
        df_selected = df.copy()

        if "treasury_balance" not in df_selected.columns:
            df_selected["treasury_balance"] = 0.0
        df_selected["treasury_balance"] = pd.to_numeric(df_selected["treasury_balance"], errors="coerce").astype(float)

        # CORRECTION : vérifier que les features enrichies existent déjà (ajoutées par add_features())
        enrich_features = [
            "tb_lag_1", "tb_lag_7", "tb_lag_30",
            "tb_rolling_7", "tb_rolling_30", 
            "tb_rolling_std_7", "tb_rolling_std_30", 
            "treasury_growth", "inflow_outflow_ratio", "expected_net_cashflow",
            "day_sin", "day_cos", "month_sin", "month_cos", "weekday_sin", "weekday_cos", 
            "is_payment_day"
        ]
        for feature in enrich_features:
            if feature not in df_selected.columns:
                df_selected[feature] = 0.0
            df_selected[feature] = pd.to_numeric(df_selected[feature], errors="coerce").astype(float)

        for feature in ["cash_inflow", "cash_outflow", "net_cashflow", "scheduled_receipts", "overdue_receipts", "scheduled_payments", "overdue_payments"]:
            if feature not in df_selected.columns:
                df_selected[feature] = 0.0
            df_selected[feature] = pd.to_numeric(df_selected[feature], errors="coerce").astype(float)

        # CORRECTION : dropna pour garantir cohérence
        df_selected = df_selected.dropna(
            subset=["tb_lag_1", "tb_lag_7", "tb_rolling_7", "tb_rolling_30"]
        )

        return df_selected[self.features]

    def split_raw_data(
        self,
        data
    ):
        """
        Time series split: TRAIN FIRST, TEST LATER.
        No shuffling - preserves temporal order.
        No leakage from future to past.
        """
        split_index = int(
            len(data) * 0.8
        )

        train_data = data.iloc[
            :split_index
        ]
        test_data = data.iloc[
            split_index:
        ]

        return (
            train_data,
            test_data
        )

    def scale_data(
        self,
        train_data,
        test_data
    ):
        """
        CRITICAL: Fit scaler ONLY on training data!
        NEVER fit on test data - that's data leakage.
        
        AutoScaler: Dynamically choose MinMaxScaler or RobustScaler based on outlier rates.
        """
        if isinstance(train_data, pd.DataFrame):
            balance_vals = train_data["treasury_balance"].dropna().to_numpy()
        else:
            balance_vals = np.asarray(train_data)[:, 0]

        if len(balance_vals) >= 10:
            q1 = np.percentile(balance_vals, 25)
            q3 = np.percentile(balance_vals, 75)
            iqr = q3 - q1
            lower_bound = q1 - 3.0 * iqr
            upper_bound = q3 + 3.0 * iqr
            
            # Count strict outliers (3.0 * IQR)
            outliers = balance_vals[(balance_vals < lower_bound) | (balance_vals > upper_bound)]
            outlier_ratio = len(outliers) / len(balance_vals)
            
            from sklearn.preprocessing import MinMaxScaler, RobustScaler
            if outlier_ratio > 0.05:
                # Many outliers: use RobustScaler
                self.scaler = RobustScaler()
            else:
                # Clean data: use MinMaxScaler
                self.scaler = MinMaxScaler()
        else:
            from sklearn.preprocessing import MinMaxScaler
            self.scaler = MinMaxScaler()

        train_scaled = self.scaler.fit_transform(
            train_data
        )

        test_scaled = self.scaler.transform(
            test_data
        )

        return (
            train_scaled,
            test_scaled
        )

    def create_sequences(
        self,
        scaled_data
    ):
        """
        Create input-output sequences for LSTM.
        Input: sequence_length days of features
        Output: next day's net_cashflow
        """
        X = []
        y = []

        for i in range(
            self.sequence_length,
            len(scaled_data)
        ):
            X.append(
                scaled_data[
                    i-self.sequence_length:i
                ]
            )

            y.append(
                scaled_data[i, 0]
            )

        X = np.array(X)
        y = np.array(y)

        return X, y
