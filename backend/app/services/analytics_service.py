"""Tenant-scoped analytics from canonical MongoDB financial_records."""

import logging

from app.utils.bson_utils import ObjectId

from app.agent.decision_engine import TreasuryDecisionAgent
from app.core.locale import DEFAULT_LOCALE, normalize_locale
from app.db import collections as c
from app.db.mongodb import database

logger = logging.getLogger(__name__)


def _record_metrics(doc: dict) -> dict:
    if "metrics" in doc:
        metrics = doc["metrics"]
        return {
            "date": doc["date"],
            "cash_inflow": float(metrics.get("cash_inflow", 0.0)),
            "cash_outflow": float(metrics.get("cash_outflow", 0.0)),
            "net_cashflow": float(metrics.get("net_cashflow", 0.0)),
            "treasury_balance": float(metrics.get("treasury_balance", 0.0)),
            "liquidity_stress": metrics.get("liquidity_stress", False),
            "liquidity_stress_score": float(metrics.get("liquidity_stress_score", 0.0)),
        }

    return {
        "date": doc["date"],
        "cash_inflow": float(doc.get("cash_inflow", doc.get("revenue", 0.0)) or 0.0),
        "cash_outflow": float(doc.get("cash_outflow", doc.get("expenses", 0.0)) or 0.0),
        "net_cashflow": float(doc.get("net_cashflow", 0.0) or 0.0),
        "treasury_balance": float(doc.get("treasury_balance", 0.0) or 0.0),
        "liquidity_stress": doc.get("liquidity_stress", False),
        "liquidity_stress_score": float(doc.get("liquidity_stress_score", 0.0) or 0.0),
    }


async def get_company_records(company_id: str, limit: int | None = None) -> list[dict]:
    """
    Load canonical treasury memory for a company.

    Source of truth: all financial_records for company_id, independent of upload_id.
    """
    cursor = database[c.FINANCIAL_RECORDS].find(
        {"company_id": ObjectId(company_id)}
    ).sort("date", 1)
    if limit:
        cursor = cursor.limit(limit)

    records = await cursor.to_list(length=limit)
    if records:
        logger.info(
            "Canonical treasury memory source: company=%s records=%s period=%s -> %s",
            company_id,
            len(records),
            records[0].get("date"),
            records[-1].get("date"),
        )
    else:
        logger.info(
            "Canonical treasury memory source: company=%s records=0 period=None",
            company_id,
        )
    return records


async def get_latest_record(company_id: str) -> dict | None:
    """Get the latest record from canonical company treasury memory."""
    return await database[c.FINANCIAL_RECORDS].find_one(
        {"company_id": ObjectId(company_id)},
        sort=[("date", -1)],
    )


async def get_treasury_context(company_id: str) -> dict | None:
    records = await get_company_records(company_id)
    if not records:
        return None

    metrics_rows = [_record_metrics(doc) for doc in records]
    latest = metrics_rows[-1]
    total_inflows = sum(row["cash_inflow"] for row in metrics_rows)
    total_outflows = sum(row["cash_outflow"] for row in metrics_rows)
    total_net_cashflow = sum(row["net_cashflow"] for row in metrics_rows)
    avg_daily_cashflow = total_net_cashflow / len(metrics_rows)
    last_30 = metrics_rows[-30:]
    avg_30d_cashflow = sum(row["net_cashflow"] for row in last_30) / len(last_30)
    first_balance = metrics_rows[0]["treasury_balance"]
    latest_balance = latest["treasury_balance"]

    return {
        "records": metrics_rows,
        "latest": latest,
        "records_loaded": len(metrics_rows),
        "date_min": metrics_rows[0]["date"],
        "date_max": metrics_rows[-1]["date"],
        "total_inflows": total_inflows,
        "total_outflows": total_outflows,
        "total_net_cashflow": total_net_cashflow,
        "avg_daily_cashflow": avg_daily_cashflow,
        "avg_30d_cashflow": avg_30d_cashflow,
        "treasury_balance": latest_balance,
        "balance_change": latest_balance - first_balance,
        "trend": "improving" if latest_balance > first_balance else "declining" if latest_balance < first_balance else "stable",
        "source": "canonical_financial_records",
    }


def _message(key: str, locale: str = DEFAULT_LOCALE) -> str:
    messages = {
        "fr": {
            "no_data": "Aucune donnée financière disponible. Importez un jeu de données financières pour commencer l'analyse.",
        },
        "en": {
            "no_data": "No financial data available. Please upload a financial dataset to begin analysis.",
        },
        "ar": {
            "no_data": "لا توجد بيانات مالية متاحة. يرجى رفع مجموعة بيانات مالية لبدء التحليل.",
        },
    }
    loc = normalize_locale(locale)
    return messages.get(loc, messages[DEFAULT_LOCALE]).get(key, key)


async def get_kpis(company_id: str, locale: str = DEFAULT_LOCALE) -> dict:
    context = await get_treasury_context(company_id)
    if not context:
        return {"message": _message("no_data", locale)}

    balance = context["treasury_balance"]
    avg_cashflow = context["avg_30d_cashflow"]
    days_until_zero = None
    if avg_cashflow < 0 and abs(avg_cashflow) > 1e-6:
        days_until_zero = int(balance / abs(avg_cashflow))

    return {
        "treasury_balance": balance,
        "net_cashflow": avg_cashflow,
        "avg_daily_cashflow": context["avg_daily_cashflow"],
        "total_inflows": context["total_inflows"],
        "total_outflows": context["total_outflows"],
        "total_net_cashflow": context["total_net_cashflow"],
        "liquidity_stress": 1.0 if balance < abs(avg_cashflow) * 30 else 0.0,
        "liquidity_stress_flag": balance < abs(avg_cashflow) * 30,
        "days_until_zero": days_until_zero,
        "cash_runway_days": days_until_zero,  # Alias for frontend compatibility
        "trend": context["trend"],
        "balance_change": context["balance_change"],
        "as_of_date": context["date_max"],
        "date_min": context["date_min"],
        "date_max": context["date_max"],
        "records_loaded": context["records_loaded"],
        "source": "canonical_financial_records",
    }


async def get_risk(company_id: str) -> dict:
    context = await get_treasury_context(company_id)
    if not context:
        return {"risk_level": "unknown"}

    agent = TreasuryDecisionAgent()
    stress = 1.0 if context["treasury_balance"] < abs(context["avg_30d_cashflow"]) * 30 else 0.0
    risk = agent.classify_risk(
        context["treasury_balance"],
        stress,
        context["avg_30d_cashflow"],
    )
    return {
        "risk_level": risk,
        "as_of_date": context["date_max"],
        "records_loaded": context["records_loaded"],
        "source": "canonical_financial_records",
    }


async def get_recommendations(company_id: str) -> dict:
    context = await get_treasury_context(company_id)
    if not context:
        return {"recommendations": []}

    stress = 1.0 if context["treasury_balance"] < abs(context["avg_30d_cashflow"]) * 30 else 0.0
    row = {
        "date": context["date_max"],
        "treasury_balance": context["treasury_balance"],
        "net_cashflow": context["avg_30d_cashflow"],
        "liquidity_stress": stress >= 0.8,
        "liquidity_stress_score": stress,
    }
    return TreasuryDecisionAgent().analyze(row)


async def list_records(
    company_id: str,
    limit: int = 90,
) -> list[dict]:
    """List records from canonical company treasury memory."""
    cursor = database[c.FINANCIAL_RECORDS].find(
        {"company_id": ObjectId(company_id)}
    ).sort("date", -1).limit(limit)

    rows = []
    async for doc in cursor:
        rows.append(_record_metrics(doc))
    return list(reversed(rows))
