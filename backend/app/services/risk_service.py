"""Persist explainable risk assessments."""

from datetime import datetime, timezone

from app.utils.bson_utils import ObjectId

from app.agent.decision_engine import TreasuryDecisionAgent
from app.db import collections as c
from app.db.mongodb import database
from app.services import analytics_service


def _utcnow():
    return datetime.now(timezone.utc)


def _build_rules_triggered(
    treasury_balance: float,
    stress_score: float,
    net_cashflow: float,
    risk_level: str,
) -> list[dict]:
    rules = []
    if treasury_balance < 0:
        rules.append(
            {
                "rule_id": "R-HIGH-01",
                "name": "negative_treasury",
                "value": treasury_balance,
            }
        )
    if stress_score >= 0.8:
        rules.append(
            {
                "rule_id": "R-HIGH-02",
                "name": "liquidity_stress_high",
                "value": stress_score,
            }
        )
    if net_cashflow < -10000:
        rules.append(
            {
                "rule_id": "R-HIGH-03",
                "name": "large_negative_cashflow",
                "value": net_cashflow,
            }
        )
    if risk_level == "medium" and treasury_balance < 300000:
        rules.append(
            {
                "rule_id": "R-MED-01",
                "name": "treasury_below_comfort",
                "threshold": 300000,
                "value": treasury_balance,
            }
        )
    if risk_level == "low" and not rules:
        rules.append(
            {
                "rule_id": "R-LOW-01",
                "name": "stable_profile",
            }
        )
    return rules


async def create_assessment(
    company_id: str,
    scenario: str | None = None,
    forecast_run_id: str | None = None,
) -> dict:
    context = await analytics_service.get_treasury_context(company_id)
    if not context:
        raise ValueError("No financial data")

    treasury_balance = context["treasury_balance"]
    net_cashflow = context["avg_30d_cashflow"]
    stress = 1.0 if treasury_balance < abs(net_cashflow) * 30 else 0.0

    agent = TreasuryDecisionAgent()
    risk_level = agent.classify_risk(
        treasury_balance,
        stress,
        net_cashflow,
    )

    assessment = {
        "company_id": ObjectId(company_id),
        "as_of_date": context["date_max"],
        "scenario": scenario,
        "risk_level": risk_level,
        "inputs": {
            "treasury_balance": treasury_balance,
            "net_cashflow": net_cashflow,
            "liquidity_stress_score": float(stress),
            "records_loaded": context["records_loaded"],
            "date_min": context["date_min"],
            "date_max": context["date_max"],
        },
        "rules_triggered": _build_rules_triggered(
            treasury_balance,
            float(stress),
            net_cashflow,
            risk_level,
        ),
        "explainability": {
            "summary_fr": f"Niveau de risque {risk_level} au {context['date_max']}.",
            "version": "rules_v1",
        },
        "treasury_memory": {
            "source": "canonical_financial_records",
            "records_loaded": context["records_loaded"],
            "date_min": context["date_min"],
            "date_max": context["date_max"],
        },
        "source_forecast_run_id": (
            ObjectId(forecast_run_id) if forecast_run_id else None
        ),
        "created_at": _utcnow(),
    }

    try:
        result = await database[c.RISK_ASSESSMENTS].insert_one(assessment)
        assessment["_id"] = result.inserted_id
    except Exception as e:
        print(f"[RISK_ASSESSMENT] Failed to store in MongoDB: {e}")
        # Return assessment without _id - caller should handle gracefully
        assessment["_id"] = None
    
    return assessment
