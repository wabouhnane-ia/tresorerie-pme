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
from app.i18n.business_intelligence_translations import (
    get_bi_translation,
    localize_business_intelligence_payload,
)


def _format_mad(value: float) -> str:
    return f"{float(value or 0):,.0f} MAD"


def _clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return int(max(minimum, min(maximum, round(value))))


def _health_label(score: int) -> tuple[str, str]:
    if score >= 90:
        return "excellent", "excellent"
    if score >= 75:
        return "healthy", "healthy"
    if score >= 60:
        return "vigilance", "vigilance"
    if score >= 40:
        return "fragile", "fragile"
    return "critical", "critical"


def _resilience_label(score: int) -> tuple[str, str]:
    """Higher score = stronger treasury resilience (easier for non-financial managers)."""
    if score >= 90:
        return "excellent", "excellent"
    if score >= 75:
        return "healthy", "healthy"
    if score >= 60:
        return "vigilance", "vigilance"
    if score >= 40:
        return "fragile", "fragile"
    return "critical", "critical"


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

    async def generate(self, company_id: str, locale: str = "fr", precomputed_context: dict | None = None) -> dict[str, Any] | None:
        locale = normalize_locale(locale)
        if precomputed_context:
            context = precomputed_context
        else:
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
        runway = self._cash_runway(context, ratios, forecast_metrics, locale)
        health = self._financial_health_score(
            context,
            forecast_metrics,
            risk_summary,
            runway,
            ratios,
            locale
        )
        resilience = self._treasury_resilience_score(
            context,
            forecast_metrics,
            risk_summary,
            runway,
            ratios,
            locale
        )
        alerts = self._smart_alerts(context, forecast_metrics, risk_summary, runway, ratios, locale)
        top_risks = self._top_risks(risk_intelligence, alerts, context, ratios, runway, locale)
        decisions = self._top_decisions(recommendations, context, runway, ratios, locale)
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
            locale=locale
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
        locale: str
    ) -> dict[str, Any]:
        """
        Estimate operating horizon from balance, inflows, outflows, burn, and trend.
        Does not use a flat 365-day cap when cash generation is positive.
        """
        balance = float(context.get("treasury_balance") or 0)
        avg_net = float(context.get("avg_30d_cashflow") or 0)
        avg_outflow = ratios["avg_daily_outflow"]
        avg_inflow = ratios["avg_daily_inflow"]
        monthly_outflows = ratios["last_outflows"]
        monthly_inflows = ratios["last_inflows"]
        trend = context.get("trend", "stable")

        if avg_net < 0 and abs(avg_net) > 1e-6:
            days = int(balance / abs(avg_net))
            method = "burn_rate"
            interpretation = get_bi_translation(
                "cash_runway.burn_rate_interpretation",
                locale,
                avg_net=_format_mad(abs(avg_net)),
                months=round(days / 30.44, 1)
            )
        elif monthly_outflows > 1e-6:
            daily_expense_pace = monthly_outflows / 30.44
            days = int(balance / daily_expense_pace)
            method = "expense_coverage"
            interpretation = get_bi_translation(
                "cash_runway.expense_coverage_interpretation",
                locale,
                balance=_format_mad(balance),
                months=round(days / 30.44, 1),
                monthly_inflows=_format_mad(monthly_inflows)
            )
        elif balance > 0:
            days = 180
            method = "stable_buffer"
            interpretation = get_bi_translation(
                "cash_runway.stable_buffer_interpretation",
                locale,
                balance=_format_mad(balance)
            )
        else:
            days = 0
            method = "insufficient_data"
            interpretation = get_bi_translation("cash_runway.insufficient_data_interpretation", locale)

        if trend == "declining":
            days = int(days * 0.8)
            interpretation += get_bi_translation("cash_runway.declining_trend_adjustment", locale)
        elif forecast_metrics.trend == "declining":
            days = int(days * 0.85)
            interpretation += get_bi_translation("cash_runway.forecast_decline_adjustment", locale)

        if avg_net > 0 and monthly_outflows > 0:
            surplus_days = int((balance + avg_net * 30) / (monthly_outflows / 30.44))
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
            "avg_daily_inflow": round(avg_inflow, 2),
            "avg_daily_outflow": round(avg_outflow, 2),
            "avg_daily_net": round(avg_net, 2),
        }

    def _financial_health_score(
        self,
        context: dict,
        forecast_metrics: ForecastMetrics,
        risk_summary: dict,
        runway: dict,
        ratios: dict,
        locale: str
    ) -> dict[str, Any]:
        balance = float(context.get("treasury_balance") or 0)
        cashflow = float(context.get("avg_30d_cashflow") or 0)
        risk_level = float(risk_summary.get("global_risk_score") or _risk_penalty(context.get("risk_level", "low")))

        liquidity_quality = min(100, max(0, runway["days"] / 180 * 100))
        stability = max(0, 100 - ratios["balance_volatility_ratio"] * 500)
        cashflow_quality = 85 if cashflow >= 0 else max(0, 60 + cashflow / max(abs(balance), 1) * 1000)
        volatility_quality = max(0, 100 - min(100, ratios["daily_volatility"] / max(abs(cashflow), 10000) * 40))
        forecast_quality = forecast_metrics.confidence_score * 100 if forecast_metrics.confidence_score else 60
        risk_quality = max(0, 100 - risk_level)

        score = _clamp(
            liquidity_quality * 0.25
            + stability * 0.15
            + cashflow_quality * 0.20
            + volatility_quality * 0.15
            + forecast_quality * 0.10
            + risk_quality * 0.15
        )
        label, category = _health_label(score)

        drivers = []
        drivers.append(get_bi_translation("health_drivers.runway", locale, months=runway["months"]))
        if cashflow >= 0:
            drivers.append(get_bi_translation("health_drivers.positive_cashflow", locale))
        else:
            drivers.append(get_bi_translation("health_drivers.negative_cashflow", locale, cashflow=_format_mad(cashflow)))
        drivers.append(get_bi_translation("health_drivers.risk_level", locale, risk_level=risk_level))

        return {
            "score": score,
            "label": get_bi_translation(f"health.{label}", locale),
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
        locale: str
    ) -> dict[str, Any]:
        """Treasury Resilience Score — higher is better (capacity to absorb shocks)."""
        cashflow = float(context.get("avg_30d_cashflow") or 0)
        risk_level = float(risk_summary.get("global_risk_score") or _risk_penalty(context.get("risk_level", "low")))
        buffer_score = min(100, runway["days"] / 180 * 100)
        operating_strength = 90 if cashflow >= 0 else max(0, 70 - min(70, abs(cashflow) / 10000))
        trend_score = 80 if forecast_metrics.trend in {"stable", "improving"} else 45
        volatility_score = max(0, 100 - ratios["daily_volatility"] / 1000)
        risk_exposure = max(0, 100 - risk_level)

        score = _clamp(
            buffer_score * 0.30
            + operating_strength * 0.25
            + trend_score * 0.15
            + volatility_score * 0.15
            + risk_exposure * 0.15
        )
        label, category = _resilience_label(score)

        drivers = []
        drivers.append(get_bi_translation("resilience_drivers.runway", locale, months=runway["months"]))
        if cashflow >= 0:
            drivers.append(get_bi_translation("resilience_drivers.positive_cashflow", locale))
        else:
            drivers.append(get_bi_translation("resilience_drivers.negative_cashflow", locale, cashflow=_format_mad(abs(cashflow))))
        if context.get("trend") == "improving":
            drivers.append(get_bi_translation("resilience_drivers.improving_trend", locale))
        elif context.get("trend") == "declining":
            drivers.append(get_bi_translation("resilience_drivers.declining_trend", locale))
        if ratios["outflow_change_pct"] > 0.1:
            drivers.append(get_bi_translation("resilience_drivers.outflow_spike", locale, pct=round(ratios["outflow_change_pct"] * 100)))
        if ratios["inflow_change_pct"] < -0.1:
            drivers.append(get_bi_translation("resilience_drivers.inflow_drop", locale, pct=abs(round(ratios["inflow_change_pct"] * 100))))

        return {
            "score": score,
            "label": get_bi_translation(f"resilience.{label}", locale),
            "category": category,
            "drivers": drivers[:5],
            "interpretation": (
                get_bi_translation("resilience_interpretation_high", locale)
                if score >= 75
                else get_bi_translation("resilience_interpretation_low", locale)
                if score < 60
                else get_bi_translation("resilience_interpretation_mid", locale)
            ),
        }

    def _smart_alerts(
        self,
        context: dict,
        forecast_metrics: ForecastMetrics,
        risk_summary: dict,
        runway: dict,
        ratios: dict,
        locale: str
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
                get_bi_translation("alerts.critical_liquidity_title", locale),
                get_bi_translation("alerts.critical_liquidity_desc", locale, days=runway["days"], interpretation=runway["interpretation"]),
                get_bi_translation("alerts.critical_liquidity_impact", locale, amount=_format_mad(ratios["avg_daily_outflow"] * min(runway["days"], 30))),
                get_bi_translation("alerts.critical_liquidity_action", locale),
                0,
            )
        elif runway["days"] < 90:
            add(
                "High",
                "liquidity",
                get_bi_translation("alerts.short_margin_title", locale),
                runway["interpretation"],
                get_bi_translation("alerts.short_margin_impact", locale),
                get_bi_translation("alerts.short_margin_action", locale),
                1,
            )

        if avg_net < 0:
            monthly_drain = abs(avg_net) * 30
            add(
                "High",
                "deterioration",
                get_bi_translation("alerts.deterioration_title", locale),
                get_bi_translation("alerts.deterioration_desc", locale, avg_net=_format_mad(abs(avg_net))),
                get_bi_translation("alerts.deterioration_impact", locale, monthly_drain=_format_mad(monthly_drain)),
                get_bi_translation("alerts.deterioration_action", locale),
                2,
            )

        if ratios["outflow_change_pct"] > 0.15:
            spike = ratios["last_outflows"] - ratios["prior_outflows"]
            add(
                "High",
                "spending",
                get_bi_translation("alerts.spending_spike_title", locale),
                get_bi_translation("alerts.spending_spike_desc", locale, pct=round(ratios["outflow_change_pct"] * 100)),
                get_bi_translation("alerts.spending_spike_impact", locale, amount=_format_mad(max(0, spike))),
                get_bi_translation("alerts.spending_spike_action", locale),
                3,
            )
        elif ratios["outflow_change_pct"] > 0.1:
            add(
                "Medium",
                "spending",
                get_bi_translation("alerts.spending_accel_title", locale),
                get_bi_translation("alerts.spending_accel_desc", locale, pct=round(ratios["outflow_change_pct"] * 100)),
                get_bi_translation("alerts.spending_accel_impact", locale),
                get_bi_translation("alerts.spending_accel_action", locale),
                4,
            )

        if ratios["inflow_change_pct"] < -0.15 or ratios.get("inflow_concentration_risk"):
            drop = max(0, ratios["prior_inflows"] - ratios["last_inflows"])
            add(
                "High",
                "concentration",
                get_bi_translation("alerts.inflow_drop_title", locale),
                get_bi_translation("alerts.inflow_drop_desc", locale, pct=abs(round(ratios["inflow_change_pct"] * 100))),
                get_bi_translation("alerts.inflow_drop_impact", locale, amount=_format_mad(drop)),
                get_bi_translation("alerts.inflow_drop_action", locale),
                5,
            )
        elif ratios["inflow_change_pct"] < -0.1:
            add(
                "Medium",
                "concentration",
                get_bi_translation("alerts.inflow_slow_title", locale),
                get_bi_translation("alerts.inflow_slow_desc", locale, pct=abs(round(ratios["inflow_change_pct"] * 100))),
                get_bi_translation("alerts.inflow_slow_impact", locale),
                get_bi_translation("alerts.inflow_slow_action", locale),
                6,
            )

        if forecast_metrics.trend == "declining" and forecast_metrics.min_balance_30d < balance:
            gap = balance - forecast_metrics.min_balance_30d
            add(
                "Medium",
                "deterioration",
                get_bi_translation("alerts.forecast_low_title", locale),
                get_bi_translation("alerts.forecast_low_desc", locale, min_balance=_format_mad(forecast_metrics.min_balance_30d)),
                get_bi_translation("alerts.forecast_low_impact", locale, amount=_format_mad(max(0, gap))),
                get_bi_translation("alerts.forecast_low_action", locale),
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
                get_bi_translation("alerts.opportunity_title", locale),
                get_bi_translation("alerts.opportunity_desc", locale, balance=_format_mad(balance)),
                get_bi_translation("alerts.opportunity_impact", locale),
                get_bi_translation("alerts.opportunity_action", locale),
                8,
            )

        if not alerts:
            add(
                "Low",
                "governance",
                get_bi_translation("alert_title", locale),
                get_bi_translation("alert_desc", locale),
                get_bi_translation("alert_impact", locale),
                get_bi_translation("alert_action", locale),
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
                return _format_mad(abs(avg_net) * min(runway["days"], 30))
            return _format_mad(balance)

        if "cashflow" in title_l or "cash" in title_l:
            return _format_mad(abs(avg_net) * 30)

        if "expense" in title_l or "dépense" in title_l or "inflation" in title_l:
            spike = max(0, ratios["last_outflows"] - ratios["prior_outflows"])
            return _format_mad(spike)

        if "revenue" in title_l or "encaissement" in title_l:
            drop = max(0, ratios["prior_inflows"] - ratios["last_inflows"])
            return _format_mad(drop)

        if "volatility" in title_l or "volatilité" in title_l:
            return _format_mad(ratios["daily_volatility"])

        return _format_mad(balance)

    def _top_risks(
        self,
        risk_intelligence: dict,
        alerts: list[dict],
        context: dict,
        ratios: dict,
        runway: dict,
        locale: str
    ) -> list[dict[str, Any]]:
        risks: list[dict[str, Any]] = []
        seen_titles: set[str] = set()

        from app.utils.locale_content import normalize_risk_intelligence, normalize_risk_entry
        risk_intelligence = normalize_risk_intelligence(risk_intelligence, locale)
        for risk in risk_intelligence.get("top_risks", [])[:3]:
            title = risk.get("title", get_bi_translation("risks.default_title", locale))
            if title in seen_titles:
                continue
            seen_titles.add(title)
            severity_score = risk.get("severity_score") or _risk_penalty(risk.get("probability", "medium"))
            if isinstance(severity_score, str):
                severity_score = _risk_penalty(severity_score)
            risks.append(
                normalize_risk_entry(
                    {
                        "title": title,
                        "severity": _severity_from_score(float(severity_score)),
                        "probability": get_bi_translation("risks.high_probability", locale) if severity_score >= 60 else get_bi_translation("risks.medium_probability", locale),
                        "estimated_financial_impact": self._estimate_financial_impact(
                            title, context, ratios, runway
                        ),
                        "impact": risk.get("impact", risk.get("business_impact", "")),
                        "urgency": get_bi_translation("urgency.30", locale),
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
                        "probability": get_bi_translation("risks.high_probability", locale)
                        if alert["severity"] in {"Critical", "High", "Critique", "Élevée"}
                        else get_bi_translation("risks.medium_probability", locale),
                        "estimated_financial_impact": alert.get("business_impact", ""),
                        "impact": alert.get("business_impact", ""),
                        "urgency": get_bi_translation("risks.immediate_urgency", locale)
                        if alert["severity"] in {"Critical", "Critique"}
                        else get_bi_translation("urgency.30", locale),
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
        locale: str
    ) -> list[dict[str, Any]]:
        decisions: list[dict[str, Any]] = []
        for rec in recommendations[:3]:
            action = rec.get("recommended_action") or rec.get("title", "")
            decisions.append(
                {
                    "action": action,
                    "expected_benefit": rec.get("expected_impact") or rec.get("business_impact", ""),
                    "urgency": rec.get("priority", get_bi_translation("probability.medium", locale)),
                    "business_justification": rec.get("why") or rec.get("reasoning", ""),
                    "time_horizon": rec.get("time_horizon", get_bi_translation("urgency.30", locale)),
                }
            )

        if not decisions:
            decisions.append(
                {
                    "action": get_bi_translation("decisions.default_action", locale),
                    "expected_benefit": get_bi_translation("decisions.default_benefit", locale),
                    "urgency": get_bi_translation("probability.low", locale),
                    "business_justification": get_bi_translation("decisions.default_justification", locale, months=runway["months"]),
                    "time_horizon": get_bi_translation("decisions.default_horizon", locale),
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
        locale: str
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
            opp_title = get_bi_translation("briefing.surplus_opportunity_title", locale)
            opp_desc = get_bi_translation("briefing.surplus_opportunity_desc", locale, balance=_format_mad(balance))
            opp_benefit = opportunity_rec.get("expected_impact") or get_bi_translation("decision_outcome", locale)
        else:
            opp_title = get_bi_translation("briefing.deficit_opportunity_title", locale)
            opp_desc = get_bi_translation("briefing.deficit_opportunity_desc", locale, avg_net=_format_mad(abs(avg_net)))
            opp_benefit = get_bi_translation("briefing.deficit_opportunity_benefit", locale)

        deterministic = {
            "executive_summary": get_bi_translation(
                "summary",
                locale,
                balance=_format_mad(balance),
                health=health["score"],
                resilience=resilience["score"],
                runway_months=runway["months"],
                risk_title=top_risk.get("title", get_bi_translation("main_risk_title", locale)),
                decision_action=top_decision.get("action", get_bi_translation("decision_action", locale))
            ),
            "financial_situation": get_bi_translation(
                "financial",
                locale,
                inflows=_format_mad(ratios["last_inflows"]),
                outflows=_format_mad(ratios["last_outflows"]),
                net=_format_mad(ratios["last_net"]),
                trend=context.get("trend", "stable")
            ),
            "main_risk": {
                "title": top_risk.get("title", get_bi_translation("main_risk_title", locale)),
                "description": top_risk.get("impact") or top_risk.get("recommended_action", ""),
                "severity": top_risk.get("severity", "Medium"),
                "estimated_financial_impact": top_risk.get("estimated_financial_impact", ""),
            },
            "main_opportunity": {
                "title": opp_title,
                "description": opp_desc,
                "potential_benefit": opp_benefit,
            },
            "cash_position_analysis": get_bi_translation(
                "cash",
                locale,
                months=runway["months"],
                label=resilience["label"],
                score=resilience["score"]
            ),
            "outlook_30_days": get_bi_translation(
                "outlook",
                locale,
                min_balance=_format_mad(forecast_metrics.min_balance_30d),
                trend=forecast_metrics.trend,
                risk_level=_risk_level({"top_risks": top_risks})
            ),
            "recommended_decision": {
                "action": top_decision.get("action", get_bi_translation("briefing.default_decision_action", locale)),
                "rationale": top_decision.get("business_justification", ""),
                "expected_outcome": top_decision.get("expected_benefit", ""),
                "urgency": top_decision.get("urgency", "Medium"),
            },
            "prediction_drivers": prediction_drivers,
            "immediate_actions": [
                {
                    "action": top_decision.get("action", ""),
                    "why": top_decision.get("business_justification", ""),
                    "deadline": top_decision.get("time_horizon", get_bi_translation("deadline", locale)),
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
                    "deadline": rec.get("time_horizon", get_bi_translation("briefing.default_decision_horizon", locale)),
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
                    "deadline": get_bi_translation("briefing.default_decision_horizon", locale),
                }
                for a in raw_executive["actions_prioritaires"]
            ]

        merged["executive_briefing"] = merged["executive_summary"]
        return merged


def _risk_level(payload: dict) -> str:
    for path in (
        ("executive_briefing", "main_risk", "severity"),
        ("top_risks", 0, "severity"),
    ):
        cur = payload
        for part in path:
            if isinstance(part, int):
                cur = cur[part] if isinstance(cur, list) and len(cur) > part else None
            else:
                cur = cur.get(part) if isinstance(cur, dict) else None
            if cur is None:
                break
        if cur:
            return str(cur)
    return "LOW"
