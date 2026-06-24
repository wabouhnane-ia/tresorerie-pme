"""
Dynamic AI Risk Intelligence Engine — Real-time financial risk analysis for SMEs.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
import logging
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class RiskLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskIntelligenceService:
    """
    Dynamic, adaptive risk intelligence engine for SME treasury management.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)

    def analyze_risk(
        self,
        df: pd.DataFrame,
        data_maturity: Dict[str, Any],
        forecast_reliability_score: int,
    ) -> Dict[str, Any]:
        """
        Complete risk intelligence analysis.

        Args:
            df: Historical financial data
            data_maturity: Data maturity analysis results
            forecast_reliability_score: Forecast reliability score (0-100)

        Returns:
            Risk intelligence dictionary
        """
        logger.info("Starting risk intelligence analysis")

        try:
            # Basic validation
            if df.empty or "treasury_balance" not in df.columns:
                return self._get_fallback_risk_result()

            # Run all analysis components
            anomaly_result = self._detect_anomalies(df)
            volatility_result = self._analyze_volatility(df)
            trend_result = self._analyze_trends(df)
            liquidity_result = self._analyze_liquidity(df)

            # Calculate dynamic risk score
            risk_score = self._calculate_risk_score(
                anomaly_result,
                volatility_result,
                trend_result,
                liquidity_result,
                forecast_reliability_score
            )

            risk_level = self._get_risk_level(risk_score)
            confidence_level = self._get_confidence_level(
                data_maturity.get("forecast_reliability_score", 50)
            )

            # Generate risk factors
            risk_factors = self._generate_risk_factors(
                anomaly_result,
                volatility_result,
                trend_result,
                liquidity_result
            )

            # Generate contextual recommendations
            recommendations = self._generate_contextual_recommendations(
                risk_factors,
                anomaly_result,
                volatility_result,
                trend_result
            )
            top_risks = self._generate_top_business_risks(
                volatility_result,
                trend_result,
                liquidity_result,
                anomaly_result,
                forecast_reliability_score,
            )

            result = {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "global_risk_level": risk_level,
                "global_risk_score": risk_score,
                "top_risks": top_risks,
                "confidence_level": confidence_level,
                "risk_factors": risk_factors,
                "anomalies_detected": anomaly_result.get("anomalies", []),
                "volatility_analysis": volatility_result,
                "trend_analysis": trend_result,
                "liquidity_analysis": liquidity_result,
                "recommendations": recommendations,
            }

            logger.info(f"Risk intelligence analysis completed: {risk_level} (score: {risk_score})")
            return result

        except Exception as e:
            logger.warning(f"Risk intelligence analysis failed: {e}", exc_info=True)
            return self._get_fallback_risk_result()

    def _detect_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect financial anomalies using Isolation Forest.

        Args:
            df: Historical financial data

        Returns:
            Anomaly detection results
        """
        try:
            # Prepare features for anomaly detection
            features = []
            if "treasury_balance" in df.columns:
                features.append("treasury_balance")
            if "net_cashflow" in df.columns:
                features.append("net_cashflow")

            if len(features) < 1 or len(df) < 20:
                return {
                    "anomaly_score": 0,
                    "anomalies": [],
                    "anomaly_count": 0
                }

            # Prepare and scale data
            df_features = df[features].dropna()
            if len(df_features) < 20:
                return {
                    "anomaly_score": 0,
                    "anomalies": [],
                    "anomaly_count": 0
                }

            scaled_data = self.scaler.fit_transform(df_features)

            # Train Isolation Forest and predict
            anomaly_labels = self.isolation_forest.fit_predict(scaled_data)
            anomaly_scores = self.isolation_forest.decision_function(scaled_data)

            # Find anomalies
            anomalies = []
            for idx, (label, score) in enumerate(zip(anomaly_labels, anomaly_scores)):
                if label == -1:  # -1 indicates anomaly
                    anomaly_type = self._classify_anomaly(df.iloc[idx], features)
                    anomalies.append({
                        "type": anomaly_type,
                        "severity": "high" if score < -0.3 else "medium",
                        "score": round(float(abs(score)), 2),
                        "date": df.iloc[idx].get("date"),
                        "message": f"Unusual financial behavior detected on {df.iloc[idx].get('date')}"
                    })

            return {
                "anomaly_score": round(np.mean(np.abs(anomaly_scores)) * 100, 2),
                "anomalies": anomalies,
                "anomaly_count": len(anomalies)
            }

        except Exception as e:
            logger.warning(f"Anomaly detection failed: {e}")
            return {
                "anomaly_score": 0,
                "anomalies": [],
                "anomaly_count": 0
            }

    def _classify_anomaly(self, row: pd.Series, features: List[str]) -> str:
        """
        Classify the type of anomaly.

        Args:
            row: Data row with anomaly
            features: List of features used

        Returns:
            Anomaly type string
        """
        if "net_cashflow" in features and pd.notna(row.get("net_cashflow")):
            if row["net_cashflow"] < 0:
                return "cash_outflow_spike"
            else:
                return "cash_inflow_spike"
        return "balance_anomaly"

    def _analyze_volatility(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze financial volatility.

        Args:
            df: Historical financial data

        Returns:
            Volatility analysis results
        """
        try:
            if "treasury_balance" not in df.columns or len(df) < 14:
                return {
                    "volatility_level": "low",
                    "stability_score": 80,
                    "rolling_std_7": 0,
                    "rolling_std_30": 0
                }

            balances = df["treasury_balance"].dropna()
            if len(balances) < 14:
                return {
                    "volatility_level": "low",
                    "stability_score": 80,
                    "rolling_std_7": 0,
                    "rolling_std_30": 0
                }

            # Calculate rolling standard deviations
            rolling_std_7 = balances.rolling(window=7).std().iloc[-1]
            rolling_std_30 = balances.rolling(window=30).std().iloc[-1] if len(balances) >= 30 else rolling_std_7

            # Calculate stability score (0-100)
            mean_balance = balances.mean()
            cv = (rolling_std_30 / (mean_balance if mean_balance != 0 else 1)) * 100
            stability_score = max(0, min(100, 100 - cv))

            # Determine volatility level
            if stability_score >= 70:
                volatility_level = "low"
            elif stability_score >= 40:
                volatility_level = "medium"
            else:
                volatility_level = "high"

            return {
                "volatility_level": volatility_level,
                "stability_score": round(stability_score, 2),
                "rolling_std_7": round(float(rolling_std_7) if pd.notna(rolling_std_7) else 0, 2),
                "rolling_std_30": round(float(rolling_std_30) if pd.notna(rolling_std_30) else 0, 2),
            }

        except Exception as e:
            logger.warning(f"Volatility analysis failed: {e}")
            return {
                "volatility_level": "low",
                "stability_score": 80,
                "rolling_std_7": 0,
                "rolling_std_30": 0
            }

    def _analyze_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze financial trends for deterioration.

        Args:
            df: Historical financial data

        Returns:
            Trend analysis results
        """
        try:
            if "treasury_balance" not in df.columns or len(df) < 14:
                return {
                    "trend_direction": "stable",
                    "trend_severity": "none",
                    "trend_score": 0
                }

            balances = df["treasury_balance"].dropna()
            if len(balances) < 14:
                return {
                    "trend_direction": "stable",
                    "trend_severity": "none",
                    "trend_score": 0
                }

            # Calculate trend using linear regression
            x = np.arange(len(balances))
            coeffs = np.polyfit(x, balances.values, 1)
            slope = coeffs[0]

            # Determine trend direction and severity
            if slope > 0:
                trend_direction = "improving"
                trend_severity = "none"
                trend_score = 0
            elif slope >= -1000:
                trend_direction = "stable"
                trend_severity = "none"
                trend_score = 20
            elif slope >= -5000:
                trend_direction = "deteriorating"
                trend_severity = "low"
                trend_score = 40
            elif slope >= -15000:
                trend_direction = "deteriorating"
                trend_severity = "medium"
                trend_score = 70
            else:
                trend_direction = "deteriorating"
                trend_severity = "high"
                trend_score = 90

            return {
                "trend_direction": trend_direction,
                "trend_severity": trend_severity,
                "trend_score": trend_score,
                "slope": round(float(slope), 2)
            }

        except Exception as e:
            logger.warning(f"Trend analysis failed: {e}")
            return {
                "trend_direction": "stable",
                "trend_severity": "none",
                "trend_score": 0
            }

    def _analyze_liquidity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze liquidity situation.

        Args:
            df: Historical financial data

        Returns:
            Liquidity analysis results
        """
        try:
            if "treasury_balance" not in df.columns:
                return {
                    "liquidity_score": 50,
                    "liquidity_level": "medium"
                }

            latest_balance = df["treasury_balance"].iloc[-1] if len(df) > 0 else 0

            # Simple liquidity scoring (can be enhanced with company-specific rules)
            if latest_balance > 500000:
                liquidity_score = 90
                liquidity_level = "very_high"
            elif latest_balance > 200000:
                liquidity_score = 70
                liquidity_level = "high"
            elif latest_balance > 100000:
                liquidity_score = 50
                liquidity_level = "medium"
            elif latest_balance > 50000:
                liquidity_score = 30
                liquidity_level = "low"
            else:
                liquidity_score = 10
                liquidity_level = "critical"

            return {
                "liquidity_score": liquidity_score,
                "liquidity_level": liquidity_level,
                "latest_balance": round(float(latest_balance), 2)
            }

        except Exception as e:
            logger.warning(f"Liquidity analysis failed: {e}")
            return {
                "liquidity_score": 50,
                "liquidity_level": "medium"
            }

    def _calculate_risk_score(
        self,
        anomaly_result: Dict[str, Any],
        volatility_result: Dict[str, Any],
        trend_result: Dict[str, Any],
        liquidity_result: Dict[str, Any],
        forecast_reliability: int
    ) -> int:
        """
        Calculate dynamic, weighted risk score (0-100).

        Args:
            anomaly_result: Anomaly detection results
            volatility_result: Volatility analysis results
            trend_result: Trend analysis results
            liquidity_result: Liquidity analysis results
            forecast_reliability: Forecast reliability score

        Returns:
            Risk score (0-100)
        """
        # Component scores (0-100, higher = riskier)
        anomaly_score = anomaly_result.get("anomaly_score", 0)
        volatility_score = 100 - volatility_result.get("stability_score", 80)
        trend_score = trend_result.get("trend_score", 0)
        liquidity_score = 100 - liquidity_result.get("liquidity_score", 50)
        forecast_penalty = (100 - forecast_reliability) * 0.3

        # Weighted average
        risk_score = (
            anomaly_score * 0.30 +
            volatility_score * 0.25 +
            trend_score * 0.20 +
            liquidity_score * 0.15 +
            forecast_penalty * 0.10
        )

        return max(0, min(100, int(risk_score)))

    def _get_risk_level(self, risk_score: int) -> str:
        """
        Get risk level from risk score.

        Args:
            risk_score: Risk score (0-100)

        Returns:
            Risk level string
        """
        if risk_score <= 25:
            return RiskLevel.LOW
        elif risk_score <= 50:
            return RiskLevel.MEDIUM
        elif risk_score <= 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _get_confidence_level(self, reliability_score: int) -> str:
        """
        Get confidence level from forecast reliability.

        Args:
            reliability_score: Forecast reliability score (0-100)

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

    def _generate_risk_factors(
        self,
        anomaly_result: Dict[str, Any],
        volatility_result: Dict[str, Any],
        trend_result: Dict[str, Any],
        liquidity_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate list of contributing risk factors.

        Returns:
            List of risk factor dictionaries
        """
        risk_factors = []

        # Trend factor
        if trend_result.get("trend_severity") != "none":
            risk_factors.append({
                "type": "trend_deterioration",
                "severity": trend_result.get("trend_severity", "low"),
                "score": trend_result.get("trend_score", 0),
                "message": f"Cash reserves are {trend_result.get('trend_direction')} consistently"
            })

        # Volatility factor
        if volatility_result.get("volatility_level") in ["medium", "high"]:
            risk_factors.append({
                "type": "volatility",
                "severity": volatility_result.get("volatility_level"),
                "score": 100 - volatility_result.get("stability_score", 80),
                "message": "High volatility detected in treasury balance"
            })

        # Liquidity factor
        if liquidity_result.get("liquidity_level") in ["low", "critical"]:
            risk_factors.append({
                "type": "liquidity_risk",
                "severity": liquidity_result.get("liquidity_level"),
                "score": 100 - liquidity_result.get("liquidity_score", 50),
                "message": "Liquidity level is concerning"
            })

        # Anomaly factor
        if anomaly_result.get("anomaly_count", 0) > 0:
            risk_factors.append({
                "type": "anomalies_detected",
                "severity": "medium",
                "score": anomaly_result.get("anomaly_score", 0),
                "message": f"{anomaly_result.get('anomaly_count', 0)} unusual financial behaviors detected"
            })

        return risk_factors

    def _generate_contextual_recommendations(
        self,
        risk_factors: List[Dict[str, Any]],
        anomaly_result: Dict[str, Any],
        volatility_result: Dict[str, Any],
        trend_result: Dict[str, Any]
    ) -> List[str]:
        """
        Generate contextual, situation-specific recommendations.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Trend-based recommendations
        if trend_result.get("trend_severity") in ["medium", "high"]:
            recommendations.append("Implement stricter cash outflow controls immediately")
            recommendations.append("Consider accelerating customer collections")

        # Volatility-based recommendations
        if volatility_result.get("volatility_level") == "high":
            recommendations.append("Increase cash buffer to handle volatile cash flows")
            recommendations.append("Implement weekly cash monitoring")

        # Anomaly-based recommendations
        if anomaly_result.get("anomaly_count", 0) > 0:
            recommendations.append("Investigate the unusual financial transactions detected")
            recommendations.append("Strengthen validation for large payments")

        # Default recommendations if nothing specific
        if len(recommendations) == 0:
            recommendations.append("Continue monitoring weekly cash position")
            recommendations.append("Maintain current cash management strategy")

        return recommendations[:5]  # Limit to 5 recommendations

    def _generate_top_business_risks(
        self,
        volatility_result: Dict[str, Any],
        trend_result: Dict[str, Any],
        liquidity_result: Dict[str, Any],
        anomaly_result: Dict[str, Any],
        forecast_reliability_score: int,
    ) -> List[Dict[str, Any]]:
        """Return the top 3 CEO-readable risks by severity."""

        liquidity_level = liquidity_result.get("liquidity_level", "medium")
        liquidity_score = 100 - liquidity_result.get("liquidity_score", 50)
        trend_score = trend_result.get("trend_score", 0)
        volatility_score = 100 - volatility_result.get("stability_score", 80)
        anomaly_score = min(100, anomaly_result.get("anomaly_count", 0) * 20)
        reliability_risk = 100 - int(forecast_reliability_score or 50)

        risks = [
            self._business_risk(
                "Liquidity Risk",
                "Available treasury may become insufficient to cover near-term operating commitments.",
                "High" if liquidity_level in ["critical", "low"] else "Medium" if liquidity_level == "medium" else "Low",
                "Potential payment delays, supplier pressure, or emergency financing need.",
                "Immediate" if liquidity_level == "critical" else "Within 30 days" if liquidity_level in ["low", "medium"] else "Monitor monthly",
                "Protect a minimum cash reserve and prepare collection or financing levers.",
                liquidity_score,
            ),
            self._business_risk(
                "Cashflow Risk",
                "Operating cash generation may not be sufficient to sustain the current treasury path.",
                "High" if trend_score >= 70 else "Medium" if trend_score >= 40 else "Low",
                "Treasury erosion and reduced management flexibility.",
                "Within 30 days" if trend_score >= 40 else "Monitor monthly",
                "Improve collections and reduce non-essential outflows.",
                trend_score,
            ),
            self._business_risk(
                "Revenue Risk",
                "Incoming cash may weaken relative to the company's spending rhythm.",
                "Medium" if trend_result.get("trend_direction") == "deteriorating" else "Low",
                "Lower cash generation and pressure on working capital.",
                "Within 30 days" if trend_result.get("trend_direction") == "deteriorating" else "Monitor monthly",
                "Prioritize confirmed collections and monitor top customer receipts.",
                max(20, trend_score - 10),
            ),
            self._business_risk(
                "Expense Inflation Risk",
                "Operating expenses may rise faster than available cash generation.",
                "Medium" if trend_score >= 40 else "Low",
                "Margin compression and avoidable cash consumption.",
                "Within 30 days" if trend_score >= 40 else "Monitor monthly",
                "Review discretionary expenses and renegotiate variable cost items.",
                max(20, trend_score - 5),
            ),
            self._business_risk(
                "Volatility Risk",
                "Cash movements may be too irregular for reliable short-term planning.",
                "High" if volatility_result.get("volatility_level") == "high" else "Medium" if volatility_result.get("volatility_level") == "medium" else "Low",
                "Unexpected cash gaps or idle liquidity.",
                "Within 30 days" if volatility_score >= 40 else "Monitor monthly",
                "Use a weekly rolling cash plan and track major inflow and outflow drivers.",
                volatility_score,
            ),
            self._business_risk(
                "Forecast Deterioration Risk",
                "The short-term treasury outlook may be weakening or insufficiently reliable for confident decisions.",
                "Medium" if reliability_risk >= 40 or trend_score >= 40 else "Low",
                "Reduced time to react and higher financing pressure.",
                "Within 30 days" if reliability_risk >= 40 or trend_score >= 40 else "Monitor monthly",
                "Trigger a management review when the 30-day low balance worsens.",
                max(reliability_risk, trend_score, anomaly_score),
            ),
        ]

        risks.sort(key=lambda item: item["_severity_score"], reverse=True)
        return [
            {key: value for key, value in risk.items() if key != "_severity_score"}
            for risk in risks[:3]
        ]

    @staticmethod
    def _business_risk(
        title: str,
        description: str,
        probability: str,
        impact: str,
        urgency: str,
        recommended_action: str,
        severity_score: float,
    ) -> Dict[str, Any]:
        return {
            "title": title,
            "description": description,
            "probability": probability,
            "impact": impact,
            "urgency": urgency,
            "recommended_action": recommended_action,
            "_severity_score": int(max(0, min(100, severity_score))),
        }

    def _get_fallback_risk_result(self) -> Dict[str, Any]:
        """
        Get fallback risk result when analysis fails.

        Returns:
            Fallback risk intelligence dictionary
        """
        return {
            "risk_level": RiskLevel.MEDIUM,
            "risk_score": 50,
            "global_risk_level": RiskLevel.MEDIUM,
            "global_risk_score": 50,
            "top_risks": [
                {
                    "title": "Liquidity Risk",
                    "description": "Treasury data is insufficient to provide a confident detailed risk ranking.",
                    "probability": "Medium",
                    "impact": "Management visibility is limited until more treasury data is available.",
                    "urgency": "Within 30 days",
                    "recommended_action": "Upload complete financial records and monitor cash weekly.",
                }
            ],
            "confidence_level": "low",
            "risk_factors": [],
            "anomalies_detected": [],
            "volatility_analysis": {
                "volatility_level": "low",
                "stability_score": 80
            },
            "trend_analysis": {
                "trend_direction": "stable",
                "trend_severity": "none"
            },
            "liquidity_analysis": {
                "liquidity_score": 50,
                "liquidity_level": "medium"
            },
            "recommendations": [
                "Continue monitoring weekly cash position"
            ]
        }
