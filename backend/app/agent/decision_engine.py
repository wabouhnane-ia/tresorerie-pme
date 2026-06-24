from app.agent.recommendation_rules import (

    RISK_RULES,

    ALERT_RULES
)


class TreasuryDecisionAgent:

    def __init__(self):

        pass

    @staticmethod
    def _stress_level(liquidity_stress) -> float:
        """
        liquidity_stress may be:
        - bool (liquidity_stress column): True/False
        - float (liquidity_stress_score): 0.0–1.0
        """
        if isinstance(liquidity_stress, (bool,)) or (
            hasattr(liquidity_stress, "dtype")
            and str(getattr(liquidity_stress, "dtype", "")) == "bool"
        ):
            return 1.0 if bool(liquidity_stress) else 0.0
        try:
            return float(liquidity_stress)
        except (TypeError, ValueError):
            return 0.0


    # ---------------------------------
    # Risk classification
    # ---------------------------------

    def classify_risk(

        self,
        treasury_balance,
        liquidity_stress,
        net_cashflow
    ):

        stress = self._stress_level(liquidity_stress)

        # High risk

        if (

            treasury_balance < 0

            or

            stress >= 0.8

            or

            net_cashflow < -10000
        ):

            return "high"


        # Medium risk

        elif (

            treasury_balance < 300000

            or

            stress >= 0.5

            or

            net_cashflow < 0
        ):

            return "medium"


        # Low risk

        else:

            return "low"


    # ---------------------------------
    # Recommendations
    # ---------------------------------

    def generate_recommendations(

        self,
        risk_level
    ):

        return RISK_RULES[
            risk_level
        ]


    # ---------------------------------
    # Alerts
    # ---------------------------------

    def generate_alert(

        self,
        risk_level
    ):

        return ALERT_RULES[
            risk_level
        ]


    # ---------------------------------
    # Main analysis
    # ---------------------------------

    def analyze(self, row):

        risk_level = self.classify_risk(

            treasury_balance=row[
                "treasury_balance"
            ],

            liquidity_stress=row.get(
                "liquidity_stress_score",
                row["liquidity_stress"],
            ),

            net_cashflow=row[
                "net_cashflow"
            ]
        )


        recommendations = (

            self.generate_recommendations(
                risk_level
            )
        )


        alert = self.generate_alert(
            risk_level
        )


        return {

            "date": row["date"],

            "risk_level": risk_level,

            "treasury_balance": row[
                "treasury_balance"
            ],

            "net_cashflow": row[
                "net_cashflow"
            ],

            "recommendations":
                recommendations,

            "alert":
                alert
        }