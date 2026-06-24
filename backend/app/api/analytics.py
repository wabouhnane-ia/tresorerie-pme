"""Tenant-scoped analytics (MongoDB). Requires JWT + active company."""

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
    company_id = ctx["company_id"]

    is_onboarding, onboarding_msg, onboarding_info = await _check_onboarding_status(company_id, locale)

    if is_onboarding:
        return {
            "has_real_data": False,
            "onboarding": True,
            "message": onboarding_msg,
            "onboarding_info": onboarding_info,
        }

    last_run = await database[c.FORECAST_RUNS].find_one(
        {"company_id": ObjectId(company_id), "status": "completed"},
        sort=[("completed_at", -1)],
    )

    kpis = await analytics_service.get_kpis(company_id, locale=locale)

    points = []
    if last_run:
        points = await forecast_db_service.get_forecast_points(company_id, limit=60)

    business_intelligence = await BusinessIntelligenceService().generate(company_id, locale=locale)

    return {
        "has_real_data": True,
        "kpis": {**kpis, "mode": "live"},
        "forecast": points,
        "business_intelligence": business_intelligence,
        "analyzed_at": last_run.get("completed_at").isoformat() if last_run and last_run.get("completed_at") else None,
        "onboarding_info": onboarding_info,
    }
