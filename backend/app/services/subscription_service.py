"""
Subscription Service — Company-level SaaS (Sprint 9).

Single plan: Intelligence Trésorerie PME
14-day trial, then expired unless activated.
Super admins bypass all checks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.utils.bson_utils import ObjectId

from app.db import collections as c
from app.db.mongodb import database

logger = logging.getLogger(__name__)

PLAN_CODE = "intelligence_tresorerie_pme"
PLAN_NAME = "Intelligence Trésorerie PME"
TRIAL_DAYS = 14
MONTHLY_PRICE_MAD = 299.0
CURRENCY = "MAD"

SUBSCRIPTION_REQUIRED_MESSAGE = (
    "Votre abonnement a expiré. Activez Intelligence Trésorerie PME "
    "pour continuer à utiliser la plateforme."
)

PLAN_FEATURES = [
    "upload_intelligent",
    "memoire_historique",
    "previsions",
    "business_intelligence",
    "decision_center",
    "notifications",
    "executive_pdf",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
    return None


def is_super_admin(user: dict) -> bool:
    return user.get("role") == "super_admin"


async def _get_plan_price() -> float:
    plan = await database[c.SUBSCRIPTION_PLANS].find_one(
        {"code": PLAN_CODE, "is_active": True}
    )
    if plan and plan.get("price_mad") is not None:
        return float(plan["price_mad"])
    return MONTHLY_PRICE_MAD


def _days_remaining(end: Optional[datetime]) -> Optional[int]:
    if end is None:
        return None
    now = _utcnow()
    delta = (end - now).total_seconds()
    if delta <= 0:
        return 0
    return max(0, int(delta // 86400) + (1 if delta % 86400 else 0))


async def create_trial_subscription(company_id: str) -> dict:
    """Create a 14-day trial subscription for a new company."""
    now = _utcnow()
    trial_end = now + timedelta(days=TRIAL_DAYS)
    doc = {
        "company_id": ObjectId(company_id),
        "status": "trial",
        "plan_code": PLAN_CODE,
        "trial_start": now,
        "trial_end": trial_end,
        "subscription_start": None,
        "subscription_end": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await database[c.SUBSCRIPTIONS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_company_subscription(company_id: str) -> Optional[dict]:
    """Fetch subscription document; lazily create trial if missing."""
    sub = await database[c.SUBSCRIPTIONS].find_one(
        {"company_id": ObjectId(company_id)}
    )
    if sub:
        return sub
    company = await database[c.COMPANIES].find_one({"_id": ObjectId(company_id)})
    if not company:
        return None
    return await create_trial_subscription(company_id)


async def ensure_subscription_current(company_id: str) -> dict:
    """Sync status when trial or paid period has ended."""
    sub = await get_company_subscription(company_id)
    if not sub:
        return sub

    now = _utcnow()
    status = sub.get("status")
    updates: dict[str, Any] = {}

    if status == "trial":
        trial_end = _parse_dt(sub.get("trial_end"))
        if trial_end and now > trial_end:
            updates["status"] = "expired"

    elif status == "active":
        sub_end = _parse_dt(sub.get("subscription_end"))
        if sub_end and now > sub_end:
            updates["status"] = "expired"

    if updates:
        updates["updated_at"] = now
        await database[c.SUBSCRIPTIONS].update_one(
            {"_id": sub["_id"]},
            {"$set": updates},
        )
        sub = await database[c.SUBSCRIPTIONS].find_one({"_id": sub["_id"]})

    return sub


async def has_active_access(company_id: str) -> bool:
    sub = await ensure_subscription_current(company_id)
    if not sub:
        return False
    return sub.get("status") in ("trial", "active")


async def activate_subscription(company_id: str) -> dict:
    """Activate paid subscription (MVP — no payment gateway)."""
    sub = await ensure_subscription_current(company_id)
    if not sub:
        sub = await create_trial_subscription(company_id)

    now = _utcnow()
    period_end = now + timedelta(days=30)

    await database[c.SUBSCRIPTIONS].update_one(
        {"_id": sub["_id"]},
        {
            "$set": {
                "status": "active",
                "subscription_start": now,
                "subscription_end": period_end,
                "updated_at": now,
            }
        },
    )
    return await database[c.SUBSCRIPTIONS].find_one({"_id": sub["_id"]})


async def cancel_subscription(company_id: str) -> dict:
    sub = await get_company_subscription(company_id)
    if not sub:
        raise ValueError("Subscription not found")

    now = _utcnow()
    await database[c.SUBSCRIPTIONS].update_one(
        {"_id": sub["_id"]},
        {"$set": {"status": "cancelled", "updated_at": now}},
    )
    return await database[c.SUBSCRIPTIONS].find_one({"_id": sub["_id"]})


def _serialize_subscription(sub: dict, price_mad: float) -> dict:
    status = sub.get("status", "expired")
    trial_end = _parse_dt(sub.get("trial_end"))
    sub_end = _parse_dt(sub.get("subscription_end"))

    if status == "trial":
        days_remaining = _days_remaining(trial_end)
    elif status == "active":
        days_remaining = _days_remaining(sub_end)
    else:
        days_remaining = 0

    is_access_allowed = status in ("trial", "active")

    return {
        "id": str(sub["_id"]),
        "company_id": str(sub["company_id"]),
        "status": status,
        "plan_name": PLAN_NAME,
        "plan_code": PLAN_CODE,
        "trial_start": sub.get("trial_start"),
        "trial_end": sub.get("trial_end"),
        "subscription_start": sub.get("subscription_start"),
        "subscription_end": sub.get("subscription_end"),
        "days_remaining": days_remaining,
        "is_access_allowed": is_access_allowed,
        "features": PLAN_FEATURES,
        "price_mad": price_mad,
        "currency": CURRENCY,
        "created_at": sub.get("created_at"),
        "updated_at": sub.get("updated_at"),
    }


async def get_subscription_detail(company_id: str) -> dict:
    sub = await ensure_subscription_current(company_id)
    price = await _get_plan_price()
    return _serialize_subscription(sub, price)


async def get_subscription_status_summary(company_id: str) -> dict:
    detail = await get_subscription_detail(company_id)
    message = None
    if not detail["is_access_allowed"]:
        message = SUBSCRIPTION_REQUIRED_MESSAGE
    return {
        "status": detail["status"],
        "is_access_allowed": detail["is_access_allowed"],
        "days_remaining": detail["days_remaining"],
        "message": message,
    }


async def get_subscription_status(user: dict) -> dict:
    """User-facing status for frontend (company-scoped when company is active)."""
    if is_super_admin(user):
        return {
            "role": "super_admin",
            "plan": {
                "code": PLAN_CODE,
                "name": PLAN_NAME,
                "limits": {},
            },
            "usage": {
                "total_uploads": 0,
                "uploads_used": 0,
                "total_forecast_runs": 0,
            },
            "show_upgrade_banner": False,
            "status": "active",
            "is_access_allowed": True,
            "days_remaining": None,
        }

    company_id = user.get("active_company_id") or user.get("company_id")
    usage = user.get("usage") or {}
    usage_payload = {
        "total_uploads": usage.get("total_uploads", 0),
        "uploads_used": usage.get("total_uploads", 0),
        "total_forecast_runs": usage.get("total_forecast_runs", 0),
        "forecast_runs_used": usage.get("total_forecast_runs", 0),
    }

    if not company_id:
        return {
            "role": user.get("role", "owner"),
            "plan": {"code": PLAN_CODE, "name": PLAN_NAME, "limits": {}},
            "usage": usage_payload,
            "show_upgrade_banner": False,
            "status": "trial",
            "is_access_allowed": False,
            "days_remaining": TRIAL_DAYS,
            "message": "Créez une entreprise pour démarrer votre essai gratuit.",
        }

    detail = await get_subscription_detail(str(company_id))
    show_upgrade_banner = detail["status"] in ("expired", "cancelled") or (
        detail["status"] == "trial" and (detail["days_remaining"] or 0) <= 3
    )

    return {
        "role": user.get("role", "owner"),
        "plan": {
            "code": detail["plan_code"],
            "name": detail["plan_name"],
            "limits": {},
            "price_mad": detail["price_mad"],
            "features": detail["features"],
        },
        "usage": usage_payload,
        "show_upgrade_banner": show_upgrade_banner,
        "status": detail["status"],
        "is_access_allowed": detail["is_access_allowed"],
        "days_remaining": detail["days_remaining"],
        "trial_end": detail.get("trial_end"),
        "subscription_end": detail.get("subscription_end"),
    }


async def can_upload(user: dict) -> tuple[bool, Optional[str]]:
    if is_super_admin(user):
        return True, None

    company_id = user.get("active_company_id") or user.get("company_id")
    if not company_id:
        return False, "No active company. Create a company first."

    if await has_active_access(str(company_id)):
        return True, None
    return False, SUBSCRIPTION_REQUIRED_MESSAGE


async def increment_upload_usage(user_id: str) -> None:
    await database[c.USERS].update_one(
        {"_id": ObjectId(user_id)},
        {
            "$inc": {"usage.total_uploads": 1},
            "$set": {"updated_at": _utcnow()},
        },
    )


async def upgrade_to_premium(user_id: str) -> dict:
    """Backward-compatible alias: activates subscription for user's active company."""
    user = await database[c.USERS].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ValueError("User not found")
    company_id = user.get("active_company_id") or user.get("company_id")
    if not company_id:
        raise ValueError("No active company")
    await activate_subscription(str(company_id))
    return await get_subscription_status(user)


async def get_admin_subscription_analytics() -> dict:
    """Aggregate subscription metrics for super admin dashboard."""
    price = await _get_plan_price()
    pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
            }
        }
    ]
    counts = {"trial": 0, "active": 0, "expired": 0, "cancelled": 0}
    async for row in database[c.SUBSCRIPTIONS].aggregate(pipeline):
        status = row.get("_id")
        if status in counts:
            counts[status] = row["count"]

    active = counts["active"]
    mrr = round(active * price, 2)
    arr = round(mrr * 12, 2)

    return {
        "plan_code": PLAN_CODE,
        "plan_name": PLAN_NAME,
        "monthly_price_mad": price,
        "currency": CURRENCY,
        "trial_subscriptions": counts["trial"],
        "active_subscriptions": active,
        "expired_subscriptions": counts["expired"],
        "cancelled_subscriptions": counts["cancelled"],
        "total_subscriptions": sum(counts.values()),
        "mrr": mrr,
        "arr": arr,
    }
