"""
Enhanced Recommendation Service v2
Integrates hybrid recommendation engine, forecast-driven insights, and executive analysis.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.utils.bson_utils import ObjectId

from app.agent.decision_engine import TreasuryDecisionAgent
from app.db import collections as c
from app.db.mongodb import database
from app.services import analytics_service, forecast_db_service
from app.services.enhanced_recommendation_engine import EnhancedRecommendationEngine
from app.llm.recommendation_generator import generate_executive_analysis
from app.core.locale import DEFAULT_LOCALE, normalize_locale
from app.utils.locale_content import (
    disclaimer_for_locale,
    normalize_executive_analysis,
    normalize_recommendation_item,
    normalize_risk_intelligence,
)

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


async def create_recommendations(
    company_id: str,
    risk_assessment_id: Optional[ObjectId] = None,
    forecast_run_id: Optional[str] = None,
    use_llm: bool = True,
    use_forecast: bool = True,
    locale: str = DEFAULT_LOCALE,
) -> dict:
    """
    Create intelligent, forecast-driven recommendations.
    
    Combines:
    1. Forecast analysis (30-day treasury predictions)
    2. Risk assessment
    3. Rule-based engine
    4. LLM narrative generation
    
    Returns structured recommendations for storage and frontend display.
    """
    locale = normalize_locale(locale)

    # === PHASE 1A: Check if company has sufficient data ===
    try:
        context = await analytics_service.get_treasury_context(company_id)
        if not context:
            # Return empty recommendations for onboarding state
            return {
                "recommendation_id": None,
                "risk_level": "onboarding",
                "recommendations": [],
                "items": [],
                "executive_analysis": None,
                "forecast_metrics": {
                    "min_balance_30d": 0,
                    "predicted_negative_day": None,
                    "trend": "unknown",
                },
                "onboarding": True,
                "message": "Importez vos données financières pour recevoir des recommandations"
            }
    except Exception as e:
        logger.error("Recommendations generation failed for company=%s: %s", company_id, e)
        return {
            "recommendation_id": None,
            "risk_level": "unknown",
            "recommendations": [],
            "items": [],
            "executive_analysis": None,
            "forecast_metrics": {
                "min_balance_30d": 0,
                "predicted_negative_day": None,
                "trend": "unknown",
            },
            "error": str(e)
        }

    # Extract financial metrics from canonical treasury memory.
    treasury_balance = context["treasury_balance"]
    net_cashflow = context["avg_30d_cashflow"]
    stress = 1.0 if treasury_balance < abs(net_cashflow) * 30 else 0.0
    liquidity_stress = stress >= 0.8

    # Calculate risk level (for backward compatibility)
    agent = TreasuryDecisionAgent()
    risk_level = agent.classify_risk(treasury_balance, stress, net_cashflow)

    # === PHASE 1: Forecast Analysis ===
    forecast_data = []
    forecast_metrics = None
    if use_forecast:
        try:
            forecast_data = await forecast_db_service.get_forecast_points(company_id, None)
            if forecast_data:
                engine = EnhancedRecommendationEngine(locale=locale)
                forecast_metrics = engine.analyze_forecast_metrics(forecast_data, treasury_balance)
        except Exception as e:
            logger.warning("Forecast analysis skipped for company=%s: %s", company_id, e)
            # Fall back to basic metrics
            from app.services.enhanced_recommendation_engine import ForecastMetrics
            forecast_metrics = ForecastMetrics(
                min_balance_30d=treasury_balance,
                min_balance_day=0,
                balance_decline_rate=0.0,
                predicted_negative_day=None,
                volatility=0.0,
                confidence_score=0.0,
                trend="unknown",
            )

    if not forecast_metrics:
        from app.services.enhanced_recommendation_engine import ForecastMetrics
        forecast_metrics = ForecastMetrics(
            min_balance_30d=treasury_balance,
            min_balance_day=0,
            balance_decline_rate=0.0,
            predicted_negative_day=None,
            volatility=0.0,
            confidence_score=0.0,
            trend="unknown",
        )

    # === PHASE 2: Generate Structured Recommendations ===
    engine = EnhancedRecommendationEngine(locale=locale)
    structured_recs = engine.generate_recommendations(
        current_balance=treasury_balance,
        net_cashflow=net_cashflow,
        liquidity_stress=stress,
        risk_level=risk_level,
        forecast_metrics=forecast_metrics,
    )
    if hasattr(engine, "generate_risk_intelligence"):
        risk_intelligence = engine.generate_risk_intelligence(
            current_balance=treasury_balance,
            net_cashflow=net_cashflow,
            liquidity_stress=stress,
            risk_level=risk_level,
            forecast_metrics=forecast_metrics,
        )
    else:
        risk_intelligence = {}
    if not isinstance(risk_intelligence, dict):
        risk_intelligence = {}
    risk_intelligence = normalize_risk_intelligence(risk_intelligence, locale)

    # Convert to dictionaries with full metadata
    recommendation_items = [
        {
            "title": rec.title,
            "description": rec.description,
            "category": rec.category,
            "severity": rec.severity,
            "priority": rec.priority,
            "why": getattr(rec, "why", getattr(rec, "reasoning", "")),
            "reasoning": getattr(rec, "reasoning", getattr(rec, "why", "")),
            "expected_impact": getattr(rec, "expected_impact", getattr(rec, "business_impact", "")),
            "difficulty": getattr(rec, "difficulty", "Moyen"),
            "time_horizon": getattr(rec, "time_horizon", "Prochains 30 jours"),
            "recommended_action": getattr(rec, "recommended_action", rec.description),
            "confidence_score": rec.confidence_score,
            "business_impact": rec.business_impact,
            "forecast_driven": rec.forecast_driven,
            "rule_based": rec.rule_based,
            "llm_enhanced": rec.llm_enhanced,
        }
        for rec in structured_recs
    ]
    recommendation_items = [
        normalize_recommendation_item(itm, locale) for itm in recommendation_items
    ]

    # === PHASE 3: Generate AI Executive Analysis ===
    executive_analysis = None
    if use_llm:
        try:
            records = context.get("records") or []
            last_30 = records[-30:]
            last_inflows = sum(float(r.get("cash_inflow") or 0) for r in last_30)
            last_outflows = sum(float(r.get("cash_outflow") or 0) for r in last_30)
            last_net = sum(float(r.get("net_cashflow") or 0) for r in last_30)
            if net_cashflow < 0 and abs(net_cashflow) > 1e-6:
                runway_days = int(treasury_balance / abs(net_cashflow))
            elif last_outflows > 0:
                runway_days = int(treasury_balance / (last_outflows / max(len(last_30), 1)))
            else:
                runway_days = 180
            runway_days = max(0, min(runway_days, 730))

            executive_context = {
                "treasury_balance": treasury_balance,
                "avg_daily_cashflow": context["avg_daily_cashflow"],
                "avg_30d_cashflow": net_cashflow,
                "last_30d_inflows": last_inflows,
                "last_30d_outflows": last_outflows,
                "last_30d_net": last_net,
                "treasury_trend": context.get("trend"),
                "risk_level": risk_level,
                "forecast_trend": forecast_metrics.trend,
                "forecast_min_balance_30d": forecast_metrics.min_balance_30d,
                "forecast_volatility": forecast_metrics.volatility,
                "forecast_balance_decline_rate": forecast_metrics.balance_decline_rate,
                "days_until_zero": forecast_metrics.predicted_negative_day,
                "liquidity_stress": stress,
                "risk_intelligence": risk_intelligence,
                "recommendations": recommendation_items,
                "records_loaded": context["records_loaded"],
                "date_min": context["date_min"],
                "date_max": context["date_max"],
                "cash_runway": {
                    "days": runway_days,
                    "months": round(runway_days / 30.44, 1),
                    "interpretation": (
                        f"Autonomie estimée à {round(runway_days / 30.44, 1)} mois "
                        f"pour un solde de {treasury_balance:,.0f} MAD."
                    ),
                },
            }
            executive_analysis = normalize_executive_analysis(
                generate_executive_analysis(executive_context, locale=locale),
                locale,
            )
            for item in recommendation_items:
                if not item["rule_based"]:
                    item["llm_enhanced"] = True
        except Exception as e:
            logger.exception("LLM executive analysis generation failed for company=%s: %s", company_id, e)
            executive_analysis = None

    # === PHASE 4: Store Complete Dataset in MongoDB ===
    try:
        for i, itm in enumerate(recommendation_items):
            recommendation_items[i] = normalize_recommendation_item(itm, locale)

        executive_analysis = normalize_executive_analysis(executive_analysis, locale)
        risk_intelligence = normalize_risk_intelligence(risk_intelligence, locale)

        rec_doc = {
            "company_id": ObjectId(company_id),
            "as_of_date": context["date_max"],
            "forecast_run_id": forecast_run_id,
            "risk_assessment_id": risk_assessment_id,
            
            # Current state
            "state": {
                "treasury_balance": treasury_balance,
                "net_cashflow": net_cashflow,
                "liquidity_stress": stress,
                "risk_level": risk_level,
            },
            "risk_summary": {
                "risk_level": risk_level,
                "global_risk_level": risk_intelligence.get("global_risk_level"),
                "global_risk_score": risk_intelligence.get("global_risk_score"),
                "top_risks": risk_intelligence.get("top_risks", []),
                "liquidity_stress": float(stress),
                "as_of_date": context["date_max"],
                "records_loaded": context["records_loaded"],
            },
            "treasury_memory": {
                "source": "canonical_financial_records",
                "records_loaded": context["records_loaded"],
                "date_min": context["date_min"],
                "date_max": context["date_max"],
                "total_inflows": context["total_inflows"],
                "total_outflows": context["total_outflows"],
                "total_net_cashflow": context["total_net_cashflow"],
                "avg_daily_cashflow": context["avg_daily_cashflow"],
                "avg_30d_cashflow": context["avg_30d_cashflow"],
                "trend": context["trend"],
            },
            
            # Forecast analysis
            "forecast_analysis": {
                "min_balance_30d": forecast_metrics.min_balance_30d,
                "min_balance_day": forecast_metrics.min_balance_day,
                "balance_decline_rate": forecast_metrics.balance_decline_rate,
                "predicted_negative_day": forecast_metrics.predicted_negative_day,
                "volatility": forecast_metrics.volatility,
                "confidence_score": forecast_metrics.confidence_score,
                "trend": forecast_metrics.trend,
            },
            
            # Recommendations
            "recommendations": {
                "items": recommendation_items,
                "total_count": len(recommendation_items),
                "critical_count": len([r for r in recommendation_items if str(r.get("severity","")).lower() in {"critical","critique"}]),
                "high_count": len([r for r in recommendation_items if str(r.get("severity","")).lower() in {"high","élevé","elevé"}]),
            },
            "risk_intelligence": risk_intelligence,
            
            # EXECUTIVE AI TREASURY ADVISOR analysis
            "executive_analysis": executive_analysis,
            
            # Metadata
            "metadata": {
                "generated_at": _utcnow().isoformat(),
                "generated_by": "hybrid_engine_v2",
                "uses_forecast": use_forecast and bool(forecast_data),
                "uses_llm": use_llm and executive_analysis is not None,
                "version": "2.0",
                "language": locale,
            },
            
            # Compliance
            "guardrails": {
                "disclaimer": disclaimer_for_locale(locale),
                "grounded_in": ["financial_records", "forecast_data", "risk_rules", "executive_analysis"],
            },
        }

        result = await database[c.RECOMMENDATIONS].insert_one(rec_doc)
        recommendation_id = str(result.inserted_id)
    except Exception as e:
        logger.error("[RECOMMENDATIONS] Failed to store in MongoDB for company=%s: %s", company_id, e)
        recommendation_id = None

    return {
        "recommendation_id": recommendation_id,
        "risk_level": risk_level,
        "recommendations": recommendation_items,
        "items": recommendation_items,
        "executive_analysis": executive_analysis,
        "risk_summary": {
            "risk_level": risk_level,
            "global_risk_level": risk_intelligence.get("global_risk_level"),
            "global_risk_score": risk_intelligence.get("global_risk_score"),
            "top_risks": risk_intelligence.get("top_risks", []),
            "liquidity_stress": float(stress),
            "as_of_date": context["date_max"],
            "records_loaded": context["records_loaded"],
        },
        "risk_intelligence": risk_intelligence,
        "treasury_memory": {
            "records_loaded": context["records_loaded"],
            "date_min": context["date_min"],
            "date_max": context["date_max"],
            "total_inflows": context["total_inflows"],
            "total_outflows": context["total_outflows"],
            "total_net_cashflow": context["total_net_cashflow"],
            "avg_daily_cashflow": context["avg_daily_cashflow"],
            "avg_30d_cashflow": context["avg_30d_cashflow"],
            "trend": context["trend"],
            "treasury_balance": treasury_balance,
            "balance_change": context["balance_change"],
        },
        "forecast_metrics": {
            "min_balance_30d": forecast_metrics.min_balance_30d,
            "predicted_negative_day": forecast_metrics.predicted_negative_day,
            "trend": forecast_metrics.trend,
            "volatility": forecast_metrics.volatility,
            "confidence_score": forecast_metrics.confidence_score,
        },
    }
