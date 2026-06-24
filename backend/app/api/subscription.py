"""
Subscription API — Sprint 9 SaaS layer.

Endpoints:
  GET  /subscription              → Full subscription detail for active company
  GET  /subscription/status       → Lightweight access status
  POST /subscription/activate     → Activate paid subscription (MVP)
  POST /subscription/cancel       → Cancel subscription
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.auth.tenant import get_active_company_id
from app.services import audit_service
from app.services.subscription_service import (
    activate_subscription,
    cancel_subscription,
    get_subscription_detail,
    get_subscription_status_summary,
    is_super_admin,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscription", tags=["Subscription"])


@router.get("")
async def get_subscription(
    current_user: dict = Depends(get_current_user),
    company_id: str = Depends(get_active_company_id),
):
    """Return subscription details for the active company."""
    if is_super_admin(current_user):
        from app.services.subscription_service import PLAN_CODE, PLAN_FEATURES, PLAN_NAME

        return {
            "id": "super_admin",
            "company_id": company_id,
            "status": "active",
            "plan_name": PLAN_NAME,
            "plan_code": PLAN_CODE,
            "days_remaining": None,
            "is_access_allowed": True,
            "features": PLAN_FEATURES,
            "role": "super_admin",
        }
    try:
        return await get_subscription_detail(company_id)
    except Exception as exc:
        logger.error("Failed to get subscription: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load subscription") from exc


@router.get("/status")
async def subscription_status(
    current_user: dict = Depends(get_current_user),
    company_id: str = Depends(get_active_company_id),
):
    """Lightweight subscription status for access checks and banners."""
    if is_super_admin(current_user):
        return {
            "status": "active",
            "is_access_allowed": True,
            "days_remaining": None,
            "message": None,
        }
    try:
        return await get_subscription_status_summary(company_id)
    except Exception as exc:
        logger.error("Failed to get subscription status: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load status") from exc


@router.post("/activate")
async def activate(
    current_user: dict = Depends(get_current_user),
    company_id: str = Depends(get_active_company_id),
):
    """Activate Intelligence Trésorerie PME (MVP — no payment gateway)."""
    try:
        sub = await activate_subscription(company_id)
        await audit_service.log_action(
            company_id=company_id,
            user_id=current_user["_id"],
            action="subscription.activate",
            resource_type="subscription",
            resource_id=str(sub["_id"]),
        )
        detail = await get_subscription_detail(company_id)
        return {"message": "Abonnement activé", "subscription": detail}
    except Exception as exc:
        logger.error("Activation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Activation failed") from exc


@router.post("/cancel")
async def cancel(
    current_user: dict = Depends(get_current_user),
    company_id: str = Depends(get_active_company_id),
):
    """Cancel company subscription."""
    try:
        sub = await cancel_subscription(company_id)
        await audit_service.log_action(
            company_id=company_id,
            user_id=current_user["_id"],
            action="subscription.cancel",
            resource_type="subscription",
            resource_id=str(sub["_id"]),
        )
        detail = await get_subscription_detail(company_id)
        return {"message": "Abonnement annulé", "subscription": detail}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Cancel failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Cancel failed") from exc
