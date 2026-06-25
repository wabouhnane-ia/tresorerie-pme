"""Tenant-scoped analytics (MongoDB). Requires JWT + active company."""

import asyncio
import logging
from datetime import date, datetime

try:
    from bson.objectid import ObjectId
except (ImportError, ModuleNotFoundError):
    try:
        from bson import ObjectId
    except (ImportError, ModuleNotFoundError):
        class ObjectId:
            def __init__(self, oid):
                self.oid = str(oid)

            def __str__(self):
                return self.oid

from fastapi import APIRouter, Depends

from app.core.locale import resolve_locale

from app.auth.dependencies import get_current_user
from app.auth.tenant import get_tenant_context
from app.db import collections as c
from app.db.mongodb import database
from app.services import analytics_service, forecast_db_service
from app.services.business_intelligence_service import BusinessIntelligenceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics (MongoDB)"],
)


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value[:10]).date()
        except ValueError:
            return None
    return None


def _onboarding_message(status: str, locale: str, historical_months: float = 0) -> str:
    messages = {
        "fr": {
            "NO_DATA": "Aucun fichier financier importé pour le moment",
            "INSUFFICIENT_HISTORY": f"Données historiques insuffisantes : {historical_months} mois dans la mémoire de trésorerie",
            "NO_FINANCIAL_DATA": "Aucune donnée financière disponible",
        },
        "en": {
            "NO_DATA": "No financial files uploaded yet",
            "INSUFFICIENT_HISTORY": f"Insufficient historical data: {historical_months} months in treasury memory",
            "NO_FINANCIAL_DATA": "No financial data available",
        },
        "ar": {
            "NO_DATA": "لم يتم استيراد أي ملفات مالية بعد",
            "INSUFFICIENT_HISTORY": f"البيانات التاريخية غير كافية: {historical_months} شهر في ذاكرة الخزينة",
            "NO_FINANCIAL_DATA": "لا توجد بيانات مالية متاحة",
        },
    }
    return messages.get(locale, messages["fr"]).get(status, status)


async def _check_onboarding_status(company_id: str, locale: str = "fr") -> tuple[bool, str, dict]:
    memory_stats = await database[c.FINANCIAL_RECORDS].aggregate([
        {"$match": {"company_id": ObjectId(company_id)}},
        {
            "$group": {
                "_id": None,
                "records_loaded": {"$sum": 1},
                "date_min": {"$min": "$date"},
                "date_max": {"$max": "$date"},
            }
        },
    ]).to_list(1)

    if not memory_stats:
        return True, _onboarding_message("NO_DATA", locale), {
            "status": "NO_DATA",
            "historical_months": 0,
            "forecasting_enabled": False,
            "records_loaded": 0,
        }

    stats = memory_stats[0]
    date_min = _as_date(stats.get("date_min"))
    date_max = _as_date(stats.get("date_max"))
    historical_days = (date_max - date_min).days + 1 if date_min and date_max else 0
    historical_months = round(historical_days / 30.44, 1) if historical_days else 0
    forecasting_enabled = historical_months >= 24

    if not forecasting_enabled:
        return True, _onboarding_message("INSUFFICIENT_HISTORY", locale, historical_months), {
            "status": "INSUFFICIENT_HISTORY",
            "historical_months": historical_months,
            "historical_days": historical_days,
            "forecasting_enabled": False,
            "records_loaded": stats["records_loaded"],
            "date_min": str(date_min) if date_min else None,
            "date_max": str(date_max) if date_max else None,
            "source": "canonical_financial_records",
        }

    return False, "", {
        "status": "READY",
        "historical_months": historical_months,
        "historical_days": historical_days,
        "forecasting_enabled": True,
        "records_loaded": stats["records_loaded"],
        "date_min": str(date_min) if date_min else None,
        "date_max": str(date_max) if date_max else None,
        "source": "canonical_financial_records",
    }


@router.get("/subscription")
async def tenant_subscription(current_user: dict = Depends(get_current_user)):
    """Get user subscription info for frontend UX (user-based SaaS)."""
    from app.services.subscription_service import get_subscription_status

    return await get_subscription_status(current_user)


@router.get("/business-intelligence")
async def get_business_intelligence(
    ctx: dict = Depends(get_tenant_context),
    locale: str = Depends(resolve_locale),
):
    """Return the CEO-facing Business Intelligence layer."""
    is_onboarding, onboarding_msg, onboarding_info = await _check_onboarding_status(ctx["company_id"], locale)
    if is_onboarding:
        return {
            "onboarding": True,
            "message": onboarding_msg,
            "onboarding_info": onboarding_info,
        }

    payload = await BusinessIntelligenceService().generate(ctx["company_id"], locale=locale)
    if not payload:
        return {
            "onboarding": True,
            "message": _onboarding_message("NO_FINANCIAL_DATA", locale),
            "onboarding_info": onboarding_info,
        }
    return payload


@router.get("/latest-analysis")
async def latest_analysis(
    ctx: dict = Depends(get_tenant_context),
    locale: str = Depends(resolve_locale),
):
    """Return the most recent full analysis package for the authenticated company."""
    import time
    t0 = time.time()
    company_id = ctx["company_id"]

    # First, fetch company records ONCE
    t1 = time.time()
    records = await analytics_service.get_company_records(company_id)
    print(f"[PERF] get_company_records: {time.time()-t1:.2f}s")

    # Now calculate onboarding status using the records we just fetched
    t2 = time.time()
    if not records:
        is_onboarding, onboarding_msg, onboarding_info = True, _onboarding_message("NO_DATA", locale), {
            "status": "NO_DATA",
            "historical_months": 0,
            "forecasting_enabled": False,
            "records_loaded": 0,
        }
    else:
        date_min = _as_date(records[0].get("date"))
        date_max = _as_date(records[-1].get("date"))
        historical_days = (date_max - date_min).days + 1 if date_min and date_max else 0
        historical_months = round(historical_days / 30.44, 1) if historical_days else 0
        forecasting_enabled = historical_months >= 24

        if not forecasting_enabled:
            is_onboarding, onboarding_msg = True, _onboarding_message("INSUFFICIENT_HISTORY", locale, historical_months)
            onboarding_info = {
                "status": "INSUFFICIENT_HISTORY",
                "historical_months": historical_months,
                "historical_days": historical_days,
                "forecasting_enabled": False,
                "records_loaded": len(records),
                "date_min": str(date_min) if date_min else None,
                "date_max": str(date_max) if date_max else None,
                "source": "canonical_financial_records",
            }
        else:
            is_onboarding, onboarding_msg = False, ""
            onboarding_info = {
                "status": "READY",
                "historical_months": historical_months,
                "historical_days": historical_days,
                "forecasting_enabled": True,
                "records_loaded": len(records),
                "date_min": str(date_min) if date_min else None,
                "date_max": str(date_max) if date_max else None,
                "source": "canonical_financial_records",
            }

    print(f"[PERF] _check_onboarding_status (reusing records): {time.time()-t2:.2f}s")

    if is_onboarding:
        print(f"[PERF] TOTAL (onboarding): {time.time()-t0:.2f}s")
        return {
            "has_real_data": False,
            "onboarding": True,
            "message": onboarding_msg,
            "onboarding_info": onboarding_info,
        }

    # Now run other fetch operations in parallel!
    t3 = time.time()
    last_run = await database[c.FORECAST_RUNS].find_one(
        {"company_id": ObjectId(company_id), "status": "completed"},
        sort=[("completed_at", -1)],
    )

    # Create context from records we already have!
    def record_metrics(doc: dict) -> dict:
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

    metrics_rows = [record_metrics(doc) for doc in records]
    latest = metrics_rows[-1]
    total_inflows = sum(row["cash_inflow"] for row in metrics_rows)
    total_outflows = sum(row["cash_outflow"] for row in metrics_rows)
    total_net_cashflow = sum(row["net_cashflow"] for row in metrics_rows)
    avg_daily_cashflow = total_net_cashflow / len(metrics_rows)
    last_30 = metrics_rows[-30:]
    avg_30d_cashflow = sum(row["net_cashflow"] for row in last_30) / len(last_30)
    first_balance = metrics_rows[0]["treasury_balance"]
    latest_balance = latest["treasury_balance"]

    context = {
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

    # Calculate KPIs directly from context to avoid re-fetching
    balance = context["treasury_balance"]
    avg_cashflow = context["avg_30d_cashflow"]
    days_until_zero = None
    if avg_cashflow < 0 and abs(avg_cashflow) > 1e-6:
        days_until_zero = int(balance / abs(avg_cashflow))
    kpis = {
        "treasury_balance": balance,
        "net_cashflow": avg_cashflow,
        "avg_daily_cashflow": context["avg_daily_cashflow"],
        "total_inflows": context["total_inflows"],
        "total_outflows": context["total_outflows"],
        "total_net_cashflow": context["total_net_cashflow"],
        "liquidity_stress": 1.0 if balance < abs(avg_cashflow) * 30 else 0.0,
        "liquidity_stress_flag": balance < abs(avg_cashflow) * 30,
        "days_until_zero": days_until_zero,
        "cash_runway_days": days_until_zero,
        "trend": context["trend"],
        "balance_change": context["balance_change"],
        "as_of_date": context["date_max"],
        "date_min": context["date_min"],
        "date_max": context["date_max"],
        "records_loaded": context["records_loaded"],
        "source": "canonical_financial_records",
    }

    points_task = forecast_db_service.get_forecast_points(company_id, limit=60) if last_run else []
    
    if isinstance(points_task, list):
        points = points_task
    else:
        points = await points_task
    
    print(f"[PERF] last_run + forecast_points: {time.time()-t3:.2f}s")

    t4 = time.time()
    # Generate BI using the precomputed context!
    business_intelligence = await BusinessIntelligenceService().generate(company_id, locale=locale, precomputed_context=context)
    print(f"[PERF] generate BI (precomputed context): {time.time()-t4:.2f}s")

    t5 = time.time()
    # Calculate cash_flow_data from last 60 of existing records
    cash_flow_data = []
    for record in records[-60:]:
        cash_flow_data.append({
            "date": record.get("date"),
            "cash_inflow": float(record.get("cash_inflow", 0)),
            "cash_outflow": float(record.get("cash_outflow", 0)),
        })
    print(f"[PERF] cash_flow_data (from existing records): {time.time()-t5:.2f}s")

    print(f"[PERF] TOTAL: {time.time()-t0:.2f}s")

    return {
        "has_real_data": True,
        "kpis": {**kpis, "mode": "live"},
        "forecast": points,
        "business_intelligence": business_intelligence,
        "analyzed_at": last_run.get("completed_at").isoformat() if last_run and last_run.get("completed_at") else None,
        "onboarding_info": onboarding_info,
        "forecast_metadata": {
            "confidence_score": last_run.get("confidence_score", 0.6) if last_run else 0.6,
            "feature_importance": last_run.get("feature_importance", []) if last_run else [],
        },
        "cash_flow_data": cash_flow_data,
    }
