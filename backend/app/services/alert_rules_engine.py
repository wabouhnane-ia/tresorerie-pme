"""Alert Rules Engine — Intelligent alert generation based on BI metrics."""

from datetime import datetime, timezone
from typing import Any

from app.schemas.notification_schema import NotificationType, NotificationSeverity


class AlertRulesEngine:
    """
    Analyzes Business Intelligence metrics and generates appropriate alerts.
    
    Rules:
    - Resilience: drop > 5 points
    - Runway: drop > 10 days
    - Financial Health: drop > 5 points
    - Outflows: unusual spike
    - Inflows: unusual drop
    - Decision: overdue
    - Opportunities: detected
    - Success: decision completed
    """

    @staticmethod
    def analyze_metrics(
        current_bi: dict[str, Any],
        previous_bi: dict[str, Any] | None = None,
        decisions: list[dict] | None = None,
    ) -> list[dict]:
        """
        Generate alerts based on BI comparison.
        
        Args:
            current_bi: Current Business Intelligence payload
            previous_bi: Previous BI snapshot (for comparison)
            decisions: List of active decisions
            
        Returns:
            List of alert dicts ready to insert into MongoDB
        """
        alerts = []
        
        # Extract current scores
        current_health = AlertRulesEngine._get_score(current_bi, "financial_health_score")
        current_resilience = AlertRulesEngine._get_score(current_bi, "treasury_resilience_score")
        current_runway = AlertRulesEngine._get_runway_days(current_bi)
        
        # If we have previous BI, compare
        if previous_bi:
            previous_health = AlertRulesEngine._get_score(previous_bi, "financial_health_score")
            previous_resilience = AlertRulesEngine._get_score(
                previous_bi, "treasury_resilience_score"
            )
            previous_runway = AlertRulesEngine._get_runway_days(previous_bi)
            
            # Rule 1: Health drop > 5 points
            health_drop = previous_health - current_health
            if health_drop > 5:
                alerts.append(
                    AlertRulesEngine._make_alert(
                        type_="warning",
                        severity="high" if health_drop > 15 else "medium",
                        title="Baisse santé financière",
                        message=f"La santé financière a baissé de {health_drop:.1f} points "
                        f"({previous_health:.0f} → {current_health:.0f}).",
                        source="business_intelligence",
                        metadata={
                            "previous_score": float(previous_health),
                            "current_score": float(current_health),
                            "drop": float(health_drop),
                        },
                    )
                )
            
            # Rule 2: Resilience drop > 5 points
            resilience_drop = previous_resilience - current_resilience
            if resilience_drop > 5:
                alerts.append(
                    AlertRulesEngine._make_alert(
                        type_="warning",
                        severity="high" if resilience_drop > 15 else "medium",
                        title="Résilience compromise",
                        message=f"La résilience de trésorerie a baissé de {resilience_drop:.1f} points "
                        f"({previous_resilience:.0f} → {current_resilience:.0f}).",
                        source="business_intelligence",
                        metadata={
                            "previous_score": float(previous_resilience),
                            "current_score": float(current_resilience),
                            "drop": float(resilience_drop),
                        },
                    )
                )
            
            # Rule 3: Runway drop > 10 days
            runway_drop = previous_runway - current_runway
            if runway_drop > 10:
                severity = "critical" if current_runway < 30 else "high" if runway_drop > 20 else "medium"
                alerts.append(
                    AlertRulesEngine._make_alert(
                        type_="risk",
                        severity=severity,
                        title="Baisse runway de trésorerie",
                        message=f"Le runway a diminué de {runway_drop:.0f} jours "
                        f"({previous_runway:.0f} → {current_runway:.0f} jours).",
                        source="business_intelligence",
                        metadata={
                            "previous_days": int(previous_runway),
                            "current_days": int(current_runway),
                            "drop_days": int(runway_drop),
                        },
                    )
                )
        
        # Rule 4: Critical runway alert (independent of comparison)
        if current_runway < 30:
            alerts.append(
                AlertRulesEngine._make_alert(
                    type_="risk",
                    severity="critical",
                    title="Runway critique détecté",
                    message=f"Runway de trésorerie critique : {current_runway:.0f} jours seulement.",
                    source="business_intelligence",
                    metadata={"runway_days": int(current_runway)},
                )
            )
        
        # Rule 5: Check for unusual outflows
        smart_alerts = current_bi.get("smart_alerts") or []
        for alert in smart_alerts:
            if "décaissement" in str(alert).lower() or "outflow" in str(alert).lower():
                alerts.append(
                    AlertRulesEngine._make_alert(
                        type_="warning",
                        severity="medium",
                        title="Décaissement inhabituel détecté",
                        message=str(alert.get("message")) if isinstance(alert, dict) else str(alert),
                        source="business_intelligence",
                        metadata=alert if isinstance(alert, dict) else {},
                    )
                )
        
        # Rule 6: Check for unusual inflows drop
        for alert in smart_alerts:
            if "encaissement" in str(alert).lower() or "inflow" in str(alert).lower():
                alerts.append(
                    AlertRulesEngine._make_alert(
                        type_="warning",
                        severity="medium",
                        title="Encaissement inhabituel détecté",
                        message=str(alert.get("message")) if isinstance(alert, dict) else str(alert),
                        source="business_intelligence",
                        metadata=alert if isinstance(alert, dict) else {},
                    )
                )
        
        # Rule 7: Check for opportunities (high resilience/health + extra cash)
        if current_resilience > 80 and current_health > 80 and current_runway > 180:
            alerts.append(
                AlertRulesEngine._make_alert(
                    type_="opportunity",
                    severity="low",
                    title="Opportunité détectée: Excédent de trésorerie",
                    message="Situation financière excellente. Considérez l'optimisation des placements "
                    "de liquidités ou des investissements stratégiques.",
                    source="business_intelligence",
                    metadata={
                        "health": float(current_health),
                        "resilience": float(current_resilience),
                        "runway": int(current_runway),
                    },
                )
            )
        
        # Rule 8: Check for overdue decisions
        if decisions:
            now = datetime.now(timezone.utc)
            for decision in decisions:
                if decision.get("status") == "pending":
                    created_at_str = decision.get("created_at")
                    if isinstance(created_at_str, str):
                        try:
                            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                            days_pending = (now - created_at).days
                            if days_pending > 14:
                                alerts.append(
                                    AlertRulesEngine._make_alert(
                                        type_="warning",
                                        severity="medium",
                                        title="Décision en attente depuis trop longtemps",
                                        message=f"Décision '{decision.get('decision_title')}' en attente "
                                        f"depuis {days_pending} jours.",
                                        source="decision_center",
                                        metadata={
                                            "decision_id": decision.get("id"),
                                            "days_pending": days_pending,
                                            "title": decision.get("decision_title"),
                                        },
                                    )
                                )
                        except Exception:
                            pass
        
        return alerts

    @staticmethod
    def _make_alert(
        type_: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        source: str,
        metadata: dict | None = None,
    ) -> dict:
        """Create an alert dict ready for MongoDB insertion."""
        return {
            "type": type_,
            "severity": severity,
            "title": title,
            "message": message,
            "source": source,
            "is_read": False,
            "created_at": datetime.now(timezone.utc),
            "expires_at": None,
            "metadata": metadata or {},
        }

    @staticmethod
    def _get_score(bi: dict[str, Any], score_name: str) -> float:
        """Extract score from BI payload, handling nested structure."""
        score_data = bi.get(score_name) or {}
        if isinstance(score_data, dict):
            return float(score_data.get("score") or 0)
        return float(score_data or 0)

    @staticmethod
    def _get_runway_days(bi: dict[str, Any]) -> int:
        """Extract runway days from BI payload."""
        runway_data = bi.get("cash_runway") or {}
        if isinstance(runway_data, dict):
            return int(runway_data.get("days") or 0)
        return int(runway_data or 0)


async def generate_success_alert(
    decision_id: str,
    decision_title: str,
    impact: dict[str, Any] | None = None,
) -> dict:
    """Generate a success alert when a decision is completed."""
    message_parts = [f"Décision '{decision_title}' réalisée avec succès."]
    
    if impact:
        deltas = []
        if impact.get("health_delta"):
            deltas.append(f"+{impact.get('health_delta')} points de santé")
        if impact.get("resilience_delta"):
            deltas.append(f"+{impact.get('resilience_delta')} points de résilience")
        if impact.get("runway_delta"):
            deltas.append(f"+{impact.get('runway_delta')} jours de runway")
        
        if deltas:
            message_parts.append("Impact mesuré: " + ", ".join(deltas))
    
    return {
        "type": "success",
        "severity": "low",
        "title": "Décision réalisée",
        "message": " ".join(message_parts),
        "source": "decision_center",
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
        "expires_at": None,
        "metadata": {
            "decision_id": decision_id,
            "impact": impact or {},
        },
    }
