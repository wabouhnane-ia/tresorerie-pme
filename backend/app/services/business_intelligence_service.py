"""Business Intelligence V3 — executive Digital CFO layer for SME managers."""

from __future__ import annotations

import statistics
from typing import Any

from app.utils.bson_utils import ObjectId
from app.db import collections as c
from app.db.mongodb import database
from app.services import analytics_service, forecast_db_service
from app.services.enhanced_recommendation_engine import EnhancedRecommendationEngine, ForecastMetrics
from app.core.locale import normalize_locale
from app.i18n.business_intelligence_translations import localize_business_intelligence_payload
from app.utils.locale_content import normalize_risk_entry, normalize_risk_intelligence


def _format_mad(value: float) -> str:
    return f"{float(value or 0):,.0f} MAD"


def _clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return int(max(minimum, min(maximum, round(value))))


def _health_label(score: int) -> tuple[str, str]:
    if score >= 90:
        return "Excellente santé financière", "excellent"
    if score >= 75:
        return "Bonne santé financière", "healthy"
    if score >= 60:
        return "Vigilance", "vigilance"
    if score >= 40:
        return "Situation fragile", "fragile"
    return "Situation critique", "critical"


def _resilience_label(score: int) -> tuple[str, str]:
    """Higher score = stronger treasury resilience (easier for non-financial managers)."""
    if score >= 90:
        return "Très forte", "excellent"
    if score >= 75:
        return "Forte", "healthy"
    if score >= 60:
        return "Modérée", "vigilance"
    if score >= 40:
        return "Faible", "fragile"
    return "Critique", "critical"


def _runway_level(days: int) -> str:
    if days < 30:
        return "critical"
    if days < 90:
        return "fragile"
    if days < 180:
        return "moderate"
    return "comfortable"


def _risk_penalty(risk_level: str) -> int:
    return {
        "critical": 80,
        "high": 60,
        "medium": 35,
        "low": 10,
        "CRITICAL": 80,
        "HIGH": 60,
        "MEDIUM": 35,
        "LOW": 10,
    }.get(risk_level, 25)


def _severity_from_score(score: float) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


class BusinessIntelligenceService:
    """Builds the V3 executive Business Intelligence payload."""

    async def generate(self, company_id: str, locale: str = "fr") -> dict[str, Any] | None:
        locale = normalize_locale(locale)
        context = await analytics_service.get_treasury_context(company_id)
        if not context:
            return None

        forecast_points = await self._get_forecast_points(company_id)
        engine = EnhancedRecommendationEngine(locale=locale)
        forecast_metrics = engine.analyze_forecast_metrics(
            forecast_points,
            context["treasury_balance"],
        )

        # Override confidence score with the scientific score from the latest forecast run if available
        latest_run = await database[c.FORECAST_RUNS].find_one(
            {"company_id": ObjectId(company_id), "status": "completed"},
            sort=[("completed_at", -1)]
        )
        
        prediction_drivers = []
        if latest_run:
            if latest_run.get("confidence_score") is not None:
                forecast_metrics.confidence_score = float(latest_run["confidence_score"])
            if latest_run.get("feature_importance"):
                prediction_drivers = latest_run["feature_importance"]

        recommendations_payload = await self._get_latest_recommendations(company_id)
        risk_summary = recommendations_payload.get("risk_summary") or {}
        risk_intelligence = recommendations_payload.get("risk_intelligence") or {}
        recommendations = recommendations_payload.get("recommendations") or []

        records = context.get("records") or []
        ratios = self._period_ratios(records)
        runway = self._cash_runway(context, ratios, forecast_metrics)
        health = self._financial_health_score(
            context,
            forecast_metrics,
            risk_summary,
            runway,
            ratios,
        )
        resilience = self._treasury_resilience_score(
            context,
            forecast_metrics,
            risk_summary,
            runway,
            ratios,
        )
        alerts = self._smart_alerts(context, forecast_metrics, risk_summary, runway, ratios)
        top_risks = self._top_risks(risk_intelligence, alerts, context, ratios, runway, locale)
        decisions = self._top_decisions(recommendations, context, runway, ratios)
        raw_executive = recommendations_payload.get("executive_analysis")
        executive_briefing = self._build_executive_briefing_v3(
            raw_executive=raw_executive,
            context=context,
            ratios=ratios,
            runway=runway,
            health=health,
            resilience=resilience,
            risk_intelligence=risk_intelligence,
            risk_summary=risk_summary,
            forecast_metrics=forecast_metrics,
            recommendations=recommendations,
            top_risks=top_risks,
            decisions=decisions,
            prediction_drivers=prediction_drivers,
        )

        payload = {
            "financial_health_score": health,
            "treasury_resilience_score": resilience,
            "cash_runway": runway,
            "smart_alerts": alerts[:5],
            "top_risks": top_risks[:3],
            "top_decisions": decisions[:3],
            "executive_briefing": executive_briefing,
        }
        return localize_business_intelligence_payload(payload, locale)

    async def _get_forecast_points(self, company_id: str) -> list[dict]:
        try:
            return await forecast_db_service.get_forecast_points(company_id, None)
        except Exception:
            return []

    async def _get_latest_recommendations(self, company_id: str) -> dict[str, Any]:
        """Read the latest stored recommendations without generating new records."""
        doc = await database[c.RECOMMENDATIONS].find_one(
            {"company_id": ObjectId(company_id)},
            sort=[("metadata.generated_at", -1), ("created_at", -1)],
        )
        if not doc:
            return {}

        recommendations = doc.get("recommendations") or []
        if isinstance(recommendations, dict):
            recommendations = recommendations.get("items") or []

        return {
            "recommendations": recommendations,
            "risk_summary": doc.get("risk_summary") or {},
            "risk_intelligence": doc.get("risk_intelligence") or {},
            "executive_analysis": doc.get("executive_analysis"),
        }

    def _period_ratios(self, records: list[dict]) -> dict[str, float]:
        last_30 = records[-30:]
        prior_30 = records[-60:-30]

        def total(rows: list[dict], key: str) -> float:
            return sum(float(row.get(key) or 0) for row in rows)

        last_inflows = total(last_30, "cash_inflow")
        prior_inflows = total(prior_30, "cash_inflow")
        last_outflows = total(last_30, "cash_outflow")
        prior_outflows = total(prior_30, "cash_outflow")
        last_net = total(last_30, "net_cashflow")
        prior_net = total(prior_30, "net_cashflow")

        balances = [float(row.get("treasury_balance") or 0) for row in last_30]
        daily_net = [float(row.get("net_cashflow") or 0) for row in last_30]
        avg_balance = statistics.mean(balances) if balances else 0
        volatility = statistics.stdev(daily_net) if len(daily_net) > 1 else 0
        days_n = max(len(last_30), 1)

        return {
            "last_inflows": last_inflows,
            "prior_inflows": prior_inflows,
            "last_outflows": last_outflows,
            "prior_outflows": prior_outflows,
            "last_net": last_net,
            "prior_net": prior_net,
            "avg_daily_inflow": last_inflows / days_n,
            "avg_daily_outflow": last_outflows / days_n,
            "avg_daily_net": last_net / days_n,
            "inflow_change_pct": self._pct_change(last_inflows, prior_inflows),
            "outflow_change_pct": self._pct_change(last_outflows, prior_outflows),
            "net_change_pct": self._pct_change(last_net, prior_net),
            "balance_volatility_ratio": (volatility / abs(avg_balance)) if avg_balance else 0,
            "daily_volatility": volatility,
            "inflow_concentration_risk": (
                last_inflows > 0 and prior_inflows > 0 and last_inflows < prior_inflows * 0.7
            ),
        }

    @staticmethod
    def _pct_change(current: float, previous: float) -> float:
        if abs(previous) < 1e-6:
            return 0.0
        return (current - previous) / abs(previous)

    def _cash_runway(
        self,
        context: dict,
        ratios: dict,
        forecast_metrics: ForecastMetrics,
    ) -> dict[str, Any]:
        """
        Estimate operating horizon from balance, inflows, outflows, burn, and trend.
        Does not use a flat 365-day cap when cash generation is positive.
        """
        balance = float(context.get("treasury_balance") or 0)
        avg_daily_net = float(context.get("avg_30d_cashflow") or 0)
        avg_daily_outflow = ratios["avg_daily_outflow"]
        avg_daily_inflow = ratios["avg_daily_inflow"]
        monthly_outflows = ratios["last_outflows"]
        monthly_inflows = ratios["last_inflows"]
        trend = context.get("trend", "stable")

        if avg_daily_net < 0 and abs(avg_daily_net) > 1e-6:
            days = int(balance / abs(avg_daily_net))
            method = "burn_rate"
            interpretation = (
                f"Au rythme actuel de consommation ({_format_mad(abs(avg_daily_net))} par jour), "
                f"la trésorerie couvre environ {round(days / 30.44, 1)} mois d'activité."
            )
        elif monthly_outflows > 1e-6:
            daily_expense_pace = monthly_outflows / 30.44
            days = int(balance / daily_expense_pace)
            method = "expense_coverage"
            interpretation = (
                f"La trésorerie actuelle ({_format_mad(balance)}) couvre environ "
                f"{round(days / 30.44, 1)} mois de dépenses au rythme des 30 derniers jours "
                f"(encaissements récents : {_format_mad(monthly_inflows)})."
            )
        elif balance > 0:
            days = 180
            method = "stable_buffer"
            interpretation = (
                f"Trésorerie disponible de {_format_mad(balance)} sans sorties significatives "
                "enregistrées sur la période récente."
            )
        else:
            days = 0
            method = "insufficient_data"
            interpretation = "Données insuffisantes pour estimer l'autonomie de trésorerie."

        if trend == "declining":
            days = int(days * 0.8)
            interpretation += " Ajustement prudent : la trésorerie recule sur la période observée."
        elif forecast_metrics.trend == "declining":
            days = int(days * 0.85)
            interpretation += " La trajectoire récente suggère une marge de sécurité à resserrer."

        if avg_daily_net > 0 and monthly_outflows > 0:
            surplus_days = int((balance + avg_daily_net * 30) / (monthly_outflows / 30.44))
            days = max(days, min(surplus_days, 730))

        days = max(0, min(days, 730))
        months = round(days / 30.44, 1)
        level = _runway_level(days)

        return {
            "days": days,
            "months": months,
            "level": level,
            "interpretation": interpretation,
            "method": method,
            "avg_daily_inflow": round(avg_daily_inflow, 2),
            "avg_daily_outflow": round(avg_daily_outflow, 2),
            "avg_daily_net": round(avg_daily_net, 2),
        }

    def _financial_health_score(
        self,
        context: dict,
        forecast_metrics: ForecastMetrics,
        risk_summary: dict,
        runway: dict,
        ratios: dict,
    ) -> dict[str, Any]:
        balance = float(context.get("treasury_balance") or 0)
        cashflow = float(context.get("avg_30d_cashflow") or 0)
        risk_score = float(risk_summary.get("global_risk_score") or _risk_penalty(context.get("risk_level", "low")))

        liquidity_quality = min(100, max(0, runway["days"] / 180 * 100))
        stability = max(0, 100 - ratios["balance_volatility_ratio"] * 500)
        cashflow_quality = 85 if cashflow > 0 else max(0, 60 + cashflow / max(abs(balance), 1) * 1000)
        volatility_quality = max(0, 100 - min(100, ratios["daily_volatility"] / max(abs(cashflow), 10000) * 40))
        forecast_quality = forecast_metrics.confidence_score * 100 if forecast_metrics.confidence_score else 60
        risk_quality = max(0, 100 - risk_score)

        score = _clamp(
            liquidity_quality * 0.25
            + stability * 0.15
            + cashflow_quality * 0.20
            + volatility_quality * 0.15
            + forecast_quality * 0.10
            + risk_quality * 0.15
        )
        label, category = _health_label(score)

        drivers = [
            f"Autonomie estimée : {runway['months']} mois.",
            "Flux net récent positif." if cashflow >= 0 else f"Flux net récent négatif : {_format_mad(cashflow)} par jour.",
            f"Niveau de risque global : {risk_summary.get('global_risk_level', 'LOW')}.",
        ]

        return {
            "score": score,
            "label": label,
            "category": category,
            "explanation": " ".join(drivers),
            "methodology": {
                "liquidity_quality": round(liquidity_quality, 1),
                "treasury_stability": round(stability, 1),
                "cashflow_quality": round(cashflow_quality, 1),
                "volatility": round(volatility_quality, 1),
                "forecast_confidence": round(forecast_quality, 1),
                "risk_exposure": round(risk_quality, 1),
            },
        }

    def _treasury_resilience_score(
        self,
        context: dict,
        forecast_metrics: ForecastMetrics,
        risk_summary: dict,
        runway: dict,
        ratios: dict,
    ) -> dict[str, Any]:
        """Treasury Resilience Score — higher is better (capacity to absorb shocks)."""
        cashflow = float(context.get("avg_30d_cashflow") or 0)
        risk_score = float(risk_summary.get("global_risk_score") or _risk_penalty(context.get("risk_level", "low")))
        buffer_score = min(100, runway["days"] / 180 * 100)
        operating_strength = 90 if cashflow >= 0 else max(0, 70 - min(70, abs(cashflow) / 10000))
        trend_score = 80 if forecast_metrics.trend in {"stable", "improving"} else 45
        volatility_score = max(0, 100 - ratios["daily_volatility"] / 1000)
        risk_exposure = max(0, 100 - risk_score)

        score = _clamp(
            buffer_score * 0.30
            + operating_strength * 0.25
            + trend_score * 0.15
            + volatility_score * 0.15
            + risk_exposure * 0.15
        )
        label, category = _resilience_label(score)

        drivers = [
            f"Horizon de trésorerie estimé : {runway['months']} mois.",
            "Les encaissements couvrent le rythme de dépenses récent." if cashflow >= 0 else f"Consommation nette de {_format_mad(abs(cashflow))} par jour.",
        ]
        if context.get("trend") == "improving":
            drivers.append("La trésorerie progresse sur la période observée.")
        elif context.get("trend") == "declining":
            drivers.append("La trésorerie recule : vigilance sur la marge de sécurité.")
        if ratios["outflow_change_pct"] > 0.1:
            drivers.append(f"Dépenses en hausse de {round(ratios['outflow_change_pct'] * 100)}% sur 30 jours.")
        if ratios["inflow_change_pct"] < -0.1:
            drivers.append(f"Encaissements en baisse de {abs(round(ratios['inflow_change_pct'] * 100))}% sur 30 jours.")

        return {
            "score": score,
            "label": label,
            "category": category,
            "drivers": drivers[:5],
            "interpretation": (
                "Capacité élevée à absorber un choc de trésorerie."
                if score >= 75
                else "Marge de sécurité limitée : des actions de direction sont à prévoir."
                if score < 60
                else "Situation gérable avec un pilotage régulier des flux."
            ),
        }

    def _smart_alerts(
        self,
        context: dict,
        forecast_metrics: ForecastMetrics,
        risk_summary: dict,
        runway: dict,
        ratios: dict,
    ) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []

        def add(
            severity: str,
            category: str,
            title: str,
            description: str,
            impact: str,
            action: str,
            priority: int,
        ):
            alerts.append(
                {
                    "severity": severity,
                    "category": category,
                    "title": title,
                    "description": description,
                    "business_impact": impact,
                    "recommended_action": action,
                    "requires_attention_today": severity in {"Critical", "High"},
                    "management_focus": description,
                }
            )

        balance = float(context.get("treasury_balance") or 0)
        avg_net = float(context.get("avg_30d_cashflow") or 0)

        if runway["days"] < 30:
            add(
                "Critical",
                "liquidity",
                "Liquidité critique à traiter aujourd'hui",
                f"Autonomie estimée à {runway['days']} jours seulement ({runway['interpretation']})",
                f"Risque de retard de paiement sur environ {_format_mad(ratios['avg_daily_outflow'] * min(runway['days'], 30))}.",
                "Bloquer les sorties non essentielles, activer les relances clients et sécuriser une ligne de trésorerie.",
                0,
            )
        elif runway["days"] < 90:
            add(
                "High",
                "liquidity",
                "Marge de trésorerie courte",
                runway["interpretation"],
                "Peu de capacité à absorber un retard client ou une dépense imprévue.",
                "Établir un plan de trésorerie sur 30 jours avec priorités de paiement.",
                1,
            )

        if avg_net < 0:
            monthly_drain = abs(avg_net) * 30
            add(
                "High",
                "deterioration",
                "La trésorerie se dégrade",
                f"Consommation nette moyenne de {_format_mad(abs(avg_net))} par jour sur 30 jours.",
                f"Érosion estimée d'environ {_format_mad(monthly_drain)} par mois si rien ne change.",
                "Réduire les charges variables et accélérer les encaissements confirmés.",
                2,
            )

        if ratios["outflow_change_pct"] > 0.15:
            spike = ratios["last_outflows"] - ratios["prior_outflows"]
            add(
                "High",
                "spending",
                "Hausse anormale des dépenses",
                f"Les sorties ont augmenté de {round(ratios['outflow_change_pct'] * 100)}% vs la période précédente.",
                f"Surcoût estimé d'environ {_format_mad(max(0, spike))} sur 30 jours.",
                "Valider chaque paiement supérieur au seuil habituel et reporter les dépenses non critiques.",
                3,
            )
        elif ratios["outflow_change_pct"] > 0.1:
            add(
                "Medium",
                "spending",
                "Dépenses en accélération",
                f"Sorties en hausse de {round(ratios['outflow_change_pct'] * 100)}% sur 30 jours.",
                "Pression sur la marge de trésorerie disponible.",
                "Revoir les postes variables et les échéances fournisseurs.",
                4,
            )

        if ratios["inflow_change_pct"] < -0.15 or ratios.get("inflow_concentration_risk"):
            drop = max(0, ratios["prior_inflows"] - ratios["last_inflows"])
            add(
                "High",
                "concentration",
                "Encaissements en forte baisse",
                f"Encaissements récents en recul de {abs(round(ratios['inflow_change_pct'] * 100))}% — dépendance accrue à quelques entrées de cash.",
                f"Manque à gagner de trésorerie d'environ {_format_mad(drop)} vs le mois précédent.",
                "Identifier les clients ou contrats en retard et sécuriser les factures à forte valeur.",
                5,
            )
        elif ratios["inflow_change_pct"] < -0.1:
            add(
                "Medium",
                "concentration",
                "Ralentissement des encaissements",
                f"Encaissements en baisse de {abs(round(ratios['inflow_change_pct'] * 100))}% sur 30 jours.",
                "Risque de tension sur le cycle de trésorerie.",
                "Relancer les créances ouvertes et confirmer les dates de paiement clients.",
                6,
            )

        if forecast_metrics.trend == "declining" and forecast_metrics.min_balance_30d < balance:
            gap = balance - forecast_metrics.min_balance_30d
            add(
                "Medium",
                "deterioration",
                "Point bas de trésorerie à venir",
                f"Le niveau de trésorerie pourrait descendre vers {_format_mad(forecast_metrics.min_balance_30d)}.",
                f"Écart potentiel d'environ {_format_mad(max(0, gap))} par rapport au solde actuel.",
                "Planifier les encaissements et reports de paiement avant la semaine de tension.",
                7,
            )

        if (
            avg_net > 0
            and balance > abs(avg_net) * 60
            and risk_summary.get("global_risk_level", "LOW") in {"LOW", "low"}
            and runway["days"] >= 120
        ):
            add(
                "Low",
                "opportunity",
                "Opportunité : optimiser l'excédent de trésorerie",
                f"Trésorerie de {_format_mad(balance)} avec génération de cash positive.",
                "Améliorer le rendement du cash excédentaire sans fragiliser les opérations.",
                "Définir une réserve opérationnelle minimale et allouer le surplus (remboursement dette, placement court terme).",
                8,
            )

        if not alerts:
            add(
                "Low",
                "governance",
                "Pilotage régulier recommandé",
                "Aucun signal critique immédiat ; maintenir la visibilité hebdomadaire.",
                "Préserver la capacité de réaction de la direction.",
                "Tenir une revue trésorerie hebdomadaire avec les 5 plus gros flux entrants et sortants.",
                9,
            )

        alerts.sort(key=lambda a: (0 if a["requires_attention_today"] else 1, -{"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(a["severity"], 0)))
        return alerts

    def _estimate_financial_impact(
        self,
        title: str,
        context: dict,
        ratios: dict,
        runway: dict,
    ) -> str:
        balance = float(context.get("treasury_balance") or 0)
        avg_net = float(context.get("avg_30d_cashflow") or 0)
        title_l = (title or "").lower()

        if "liquidity" in title_l or "liquidité" in title_l:
            if avg_net < 0:
                return f"Jusqu'à {_format_mad(abs(avg_net) * min(runway['days'], 30))} de tension sur 30 jours."
            return f"Réserve actuelle {_format_mad(balance)} pour {runway['months']} mois au rythme actuel."

        if "cashflow" in title_l or "cash" in title_l:
            return f"Érosion potentielle de {_format_mad(abs(avg_net) * 30)} par mois."

        if "expense" in title_l or "dépense" in title_l or "inflation" in title_l:
            spike = max(0, ratios["last_outflows"] - ratios["prior_outflows"])
            return f"Surcoût estimé {_format_mad(spike)} sur 30 jours."

        if "revenue" in title_l or "encaissement" in title_l:
            drop = max(0, ratios["prior_inflows"] - ratios["last_inflows"])
            return f"Manque de trésorerie estimé {_format_mad(drop)} vs période précédente."

        if "volatility" in title_l or "volatilité" in title_l:
            return f"Variabilité des flux autour de {_format_mad(ratios['daily_volatility'])} par jour."

        return f"Exposition liée au solde de {_format_mad(balance)} et aux flux récents."

    def _top_risks(
        self,
        risk_intelligence: dict,
        alerts: list[dict],
        context: dict,
        ratios: dict,
        runway: dict,
        locale: str = "fr",
    ) -> list[dict[str, Any]]:
        risks: list[dict[str, Any]] = []
        seen_titles: set[str] = set()

        risk_intelligence = normalize_risk_intelligence(risk_intelligence, locale)
        for risk in risk_intelligence.get("top_risks", [])[:3]:
            title = risk.get("title", "Risque de trésorerie")
            if title in seen_titles:
                continue
            seen_titles.add(title)
            severity_score = risk.get("severity_score") or _risk_penalty(risk.get("probability", "Moyenne"))
            if isinstance(severity_score, str):
                severity_score = _risk_penalty(severity_score)
            risks.append(
                normalize_risk_entry(
                    {
                        "title": title,
                        "severity": _severity_from_score(float(severity_score)),
                        "probability": risk.get("probability", "Moyenne"),
                        "estimated_financial_impact": self._estimate_financial_impact(
                            title, context, ratios, runway
                        ),
                        "impact": risk.get("impact", risk.get("business_impact", "")),
                        "urgency": risk.get("urgency", "Sous 30 jours"),
                        "recommended_action": risk.get("recommended_action", ""),
                    },
                    locale,
                )
            )

        for alert in alerts:
            if len(risks) >= 3:
                break
            title = alert["title"]
            if title in seen_titles:
                continue
            seen_titles.add(title)
            risks.append(
                normalize_risk_entry(
                    {
                        "title": title,
                        "severity": alert["severity"],
                        "probability": "Élevée"
                        if alert["severity"] in {"Critical", "High", "Critique", "Élevée"}
                        else "Moyenne",
                        "estimated_financial_impact": alert.get("business_impact", ""),
                        "impact": alert.get("business_impact", ""),
                        "urgency": "Immédiat"
                        if alert["severity"] in {"Critical", "Critique"}
                        else "Sous 30 jours",
                        "recommended_action": alert.get("recommended_action", ""),
                    },
                    locale,
                )
            )
        return risks

    def _top_decisions(
        self,
        recommendations: list[dict],
        context: dict,
        runway: dict,
        ratios: dict,
    ) -> list[dict[str, Any]]:
        decisions: list[dict[str, Any]] = []
        for rec in recommendations[:3]:
            action = rec.get("recommended_action") or rec.get("title", "")
            decisions.append(
                {
                    "action": action,
                    "expected_benefit": rec.get("expected_impact") or rec.get("business_impact", ""),
                    "urgency": rec.get("priority", "Moyenne"),
                    "business_justification": rec.get("why") or rec.get("reasoning", ""),
                    "time_horizon": rec.get("time_horizon", "Next 30 days"),
                }
            )

        if not decisions:
            decisions.append(
                {
                    "action": "Instaurer une revue trésorerie hebdomadaire",
                    "expected_benefit": "Détecter plus tôt les tensions et prioriser les encaissements.",
                    "urgency": "Faible",
                    "business_justification": f"Autonomie estimée à {runway['months']} mois — le pilotage régulier sécurise cette position.",
                    "time_horizon": "Prochains 30 jours",
                }
            )
        return decisions

    def _build_executive_briefing_v3(
        self,
        *,
        raw_executive: dict | None,
        context: dict,
        ratios: dict,
        runway: dict,
        health: dict,
        resilience: dict,
        risk_intelligence: dict,
        risk_summary: dict,
        forecast_metrics: ForecastMetrics,
        recommendations: list[dict],
        top_risks: list[dict],
        decisions: list[dict],
        prediction_drivers: list[dict] = None,
    ) -> dict[str, Any]:
        if prediction_drivers is None:
            prediction_drivers = []
            
        balance = float(context.get("treasury_balance") or 0)
        avg_net = float(context.get("avg_30d_cashflow") or 0)
        top_risk = top_risks[0] if top_risks else {}
        top_decision = decisions[0] if decisions else {}
        main_rec = recommendations[0] if recommendations else {}

        opportunity_rec = next(
            (r for r in recommendations if (r.get("category") or "").lower() in {"cash optimization", "cash optimisation"}),
            main_rec,
        )
        if avg_net >= 0 and balance > 0:
            opp_title = "Renforcer la valeur de l'excédent de trésorerie"
            opp_desc = (
                f"Avec {_format_mad(balance)} en caisse et des encaissements qui couvrent le rythme de dépenses, "
                "la direction peut structurer une réserve minimale et utiliser le surplus."
            )
            opp_benefit = opportunity_rec.get("expected_impact") or "Améliorer le rendement du cash sans fragiliser les opérations."
        else:
            opp_title = "Accélérer les encaissements confirmés"
            opp_desc = (
                f"Prioriser les relances sur les créances ouvertes pour compenser la consommation de "
                f"{_format_mad(abs(avg_net))} par jour."
            )
            opp_benefit = "Réduire la pression sur la trésorerie dans les 30 prochains jours."

        deterministic = {
            "executive_summary": (
                f"Trésorerie à {_format_mad(balance)} — santé {health['score']}/100, "
                f"résilience {resilience['score']}/100, autonomie estimée {runway['months']} mois. "
                f"Risque principal : {top_risk.get('title', 'à surveiller')}. "
                f"Décision prioritaire : {top_decision.get('action', 'revue trésorerie hebdomadaire')}."
            ),
            "financial_situation": (
                f"Sur les 30 derniers jours : encaissements {_format_mad(ratios['last_inflows'])}, "
                f"dépenses {_format_mad(ratios['last_outflows'])}, flux net {_format_mad(ratios['last_net'])}. "
                f"Flux journalier moyen : {_format_mad(avg_net)}. "
                f"Évolution de la trésorerie : {context.get('trend', 'stable')}."
            ),
            "main_risk": {
                "title": top_risk.get("title", "Risque de trésorerie"),
                "description": top_risk.get("impact") or top_risk.get("recommended_action", ""),
                "severity": top_risk.get("severity", "Medium"),
                "estimated_financial_impact": top_risk.get("estimated_financial_impact", ""),
            },
            "main_opportunity": {
                "title": opp_title,
                "description": opp_desc,
                "potential_benefit": opp_benefit,
            },
            "cash_position_analysis": (
                f"Solde actuel {_format_mad(balance)}. "
                f"{runway['interpretation']} "
                f"Résilience : {resilience['label']} ({resilience['score']}/100)."
            ),
            "outlook_30_days": (
                f"Sur 30 jours : point bas attendu autour de {_format_mad(forecast_metrics.min_balance_30d)}, "
                f"tendance {forecast_metrics.trend}. "
                f"Niveau de risque global : {risk_summary.get('global_risk_level', 'LOW')}."
            ),
            "recommended_decision": {
                "action": top_decision.get("action", "Piloter la trésorerie en comité de direction"),
                "rationale": top_decision.get("business_justification", ""),
                "expected_outcome": top_decision.get("expected_benefit", ""),
                "urgency": top_decision.get("urgency", "Medium"),
            },
            "prediction_drivers": prediction_drivers,
            "immediate_actions": [
                {
                    "action": top_decision.get("action", ""),
                    "why": top_decision.get("business_justification", ""),
                    "deadline": top_decision.get("time_horizon", "Cette semaine"),
                }
            ],
        }

        for idx, rec in enumerate(recommendations[1:3], start=1):
            if len(deterministic["immediate_actions"]) >= 3:
                break
            deterministic["immediate_actions"].append(
                {
                    "action": rec.get("recommended_action") or rec.get("title", ""),
                    "why": rec.get("why") or rec.get("reasoning", ""),
                    "deadline": rec.get("time_horizon", "30 jours"),
                }
            )

        if not isinstance(raw_executive, dict):
            return deterministic

        merged = {**deterministic}
        for key in (
            "executive_summary",
            "financial_situation",
            "cash_position_analysis",
            "outlook_30_days",
        ):
            if raw_executive.get(key):
                merged[key] = raw_executive[key]
            elif raw_executive.get("situation_financiere") and key == "financial_situation":
                merged[key] = raw_executive["situation_financiere"]
            elif raw_executive.get("perspectives_30_jours") and key == "outlook_30_days":
                merged[key] = raw_executive["perspectives_30_jours"]

        if raw_executive.get("executive_briefing") and not raw_executive.get("executive_summary"):
            merged["executive_summary"] = raw_executive["executive_briefing"]

        if isinstance(raw_executive.get("main_risk"), dict):
            merged["main_risk"] = {**merged["main_risk"], **raw_executive["main_risk"]}
        elif raw_executive.get("analyse_risque", {}).get("main_risk"):
            mr = raw_executive["analyse_risque"]["main_risk"]
            merged["main_risk"] = {
                **merged["main_risk"],
                "title": merged["main_risk"]["title"],
                "description": mr.get("description", merged["main_risk"]["description"]),
                "severity": raw_executive["analyse_risque"].get("global_risk_level", merged["main_risk"]["severity"]),
            }

        if isinstance(raw_executive.get("main_opportunity"), dict):
            merged["main_opportunity"] = {**merged["main_opportunity"], **raw_executive["main_opportunity"]}
        elif isinstance(raw_executive.get("opportunite_majeure"), dict):
            om = raw_executive["opportunite_majeure"]
            merged["main_opportunity"] = {
                "title": merged["main_opportunity"]["title"],
                "description": om.get("description", merged["main_opportunity"]["description"]),
                "potential_benefit": om.get("benefit", merged["main_opportunity"]["potential_benefit"]),
            }

        if isinstance(raw_executive.get("recommended_decision"), dict):
            merged["recommended_decision"] = {**merged["recommended_decision"], **raw_executive["recommended_decision"]}
        elif isinstance(raw_executive.get("decision_prioritaire"), dict):
            dp = raw_executive["decision_prioritaire"]
            merged["recommended_decision"] = {
                "action": dp.get("titre", merged["recommended_decision"]["action"]),
                "rationale": dp.get("pourquoi", merged["recommended_decision"]["rationale"]),
                "expected_outcome": dp.get("impact_attendu", merged["recommended_decision"]["expected_outcome"]),
                "urgency": merged["recommended_decision"]["urgency"],
            }

        if raw_executive.get("immediate_actions"):
            merged["immediate_actions"] = raw_executive["immediate_actions"]
        elif raw_executive.get("actions_prioritaires"):
            merged["immediate_actions"] = [
                {
                    "action": a.get("action", ""),
                    "why": a.get("pourquoi", ""),
                    "deadline": "30 jours",
                }
                for a in raw_executive["actions_prioritaires"]
            ]

        merged["executive_briefing"] = merged["executive_summary"]
        return merged
