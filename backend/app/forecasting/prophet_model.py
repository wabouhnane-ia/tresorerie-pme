import pandas as pd

from prophet import Prophet
from app.services.calendar_enrichment_service import CalendarEnrichmentService


class ProphetForecaster:

    def __init__(
        self,
        scenario=None
    ):
        """
        Prophet forecaster for treasury predictions.
        
        Args:
            scenario: Optional metadata tag (not used in model logic)
        """
        self.scenario = scenario
        self.calendar_service = CalendarEnrichmentService(country_code="MA")

        self.model = Prophet(

            yearly_seasonality=True,

            weekly_seasonality=False,  # CORRECTION : signal hebdo fictif (ratio=0.036)

            daily_seasonality=False,

            changepoint_prior_scale=0.05,  # CORRECTION : réduit (0.1→0.05)

            interval_width=0.95
        )

        # Morocco country holidays
        self.model.add_country_holidays(country_name="MA")


        # ---------------------------------
        # Monthly seasonality (experimental)
        # Added as a single controlled change for scientific evaluation only.
        # See experiment: add_seasonality(name='monthly', period=30.5, fourier_order=5)
        self.model.add_seasonality(name="monthly", period=30.5, fourier_order=5)

        # ---------------------------------
        # Deterministic regressors only (known with 100% certainty in future)
        # ---------------------------------
        self.regressors = [
            "scheduled_receipts",
            "scheduled_payments",
            "is_holiday",
            "is_ramadan",
            "is_business_day",
            "month",
            "quarter"
        ]

        self.regressor_window_days = 30

    # ---------------------------------
    # Load dataset (DEPRECATED - kept for backward compatibility)
    # ---------------------------------

    def load_dataset(self):
        """
        DEPRECATED: This method loads from CSV file.
        Current system loads data from MongoDB via forecast_db_service.
        Kept for backward compatibility only.
        """
        df = pd.read_csv(
            "data/final_treasury_dataset.csv"
        )

        # Note: scenario filtering no longer needed
        # Data is already filtered by company_id in MongoDB
        return df

    # ---------------------------------
    # Prepare Prophet dataframe
    # ---------------------------------

    def prepare_data(
        self,
        df
    ):
        # Check if already calendar-enriched
        required_calendar_cols = ["is_holiday", "is_ramadan", "is_business_day", "month", "quarter"]
        if all(col in df.columns for col in required_calendar_cols):
            df_enriched = df
        else:
            # Enrich with calendar features
            df_enriched = self.calendar_service.enrich_calendar_features(df)

        prophet_df = pd.DataFrame()

        # ---------------------------------
        # Prophet required columns
        # ---------------------------------

        prophet_df["ds"] = pd.to_datetime(
            df_enriched["date"]
        )

        prophet_df["y"] = df_enriched[
            "treasury_balance"  # CORRECTION : cible = solde de trésorerie cumulé (lisse, positif, utile métier) au lieu de net_cashflow (trop volatile, R² négatif)
        ]

        # ---------------------------------
        # Add deterministic regressors only
        # ---------------------------------
        for regressor in self.regressors:
            if regressor in df_enriched.columns:
                prophet_df[regressor] = df_enriched[regressor]
            else:
                # Initialize with 0 if not present
                prophet_df[regressor] = 0.0

        return prophet_df

    # ---------------------------------
    # Add regressors
    # ---------------------------------

    def add_regressors(self):

        for regressor in self.regressors:

            self.model.add_regressor(
                regressor
            )

    # ---------------------------------
    # Train model
    # ---------------------------------

    def train_model(
        self,
        prophet_df
    ):

        self.add_regressors()

        self.model.fit(
            prophet_df
        )

    # ---------------------------------
    # Create future dataframe
    # ---------------------------------

    def make_future_dataframe(

        self,

        prophet_df,

        periods=30
    ):

        future = self.model.make_future_dataframe(
            periods=periods
        )

        # ---------------------------------
        # Generate calendar features for all dates (historical and future)
        # ---------------------------------
        calendar_features = ["month", "quarter", "is_holiday", "is_ramadan", "is_business_day"]
        
        # Prepare a df with date column for calendar enrichment
        future_for_enrich = future.rename(columns={"ds": "date"})
        enriched = self.calendar_service.enrich_calendar_features(future_for_enrich)
        
        # Add the regenerated calendar features to future df
        for feat in calendar_features:
            if feat in enriched.columns:
                future[feat] = enriched[feat]

        # ---------------------------------
        # Scenario continuation for commitment regressors ONLY
        # ---------------------------------
        # These are business commitment regressors that are known in future,
        # we use last known value if not available
        commitment_regressors = ["scheduled_receipts", "scheduled_payments"]
        
        if self.regressors:
            # Keep only commitment regressors that are present in prophet_df
            present_commitment_regressors = [r for r in commitment_regressors if r in prophet_df.columns]
            if present_commitment_regressors:
                reg_df = prophet_df[["ds"] + present_commitment_regressors].copy()
                # Merge only commitment regressors (to avoid column conflict with calendar features)
                future = future.merge(reg_df, on="ds", how="left")

                # Find last known values from prophet_df for commitment regressors
                last_known = {}
                last_row = reg_df.dropna(how="all").tail(1)
                if not last_row.empty:
                    for r in present_commitment_regressors:
                        last_known[r] = last_row.iloc[0].get(r, 0)
                else:
                    for r in present_commitment_regressors:
                        last_known[r] = 0

                # Fill commitment regressors with last known value
                for r in present_commitment_regressors:
                    if r in future.columns:
                        if last_known.get(r) is not None:
                            future[r] = future[r].fillna(last_known[r])

        return future

    # ---------------------------------
    # Predict with uncertainty
    # ---------------------------------

    def predict(
        self,
        future
    ):

        forecast = self.model.predict(
            future
        )

        return forecast
