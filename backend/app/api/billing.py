"""
Billing API — Simplified subscription model.

Endpoints:
  GET  /billing/plans                  → Single subscription plan (Treasury Intelligence Pro)

Rules:
  - Single plan for all companies: Treasury Intelligence Pro
  - Company-level subscriptions (not user-level)
  - Admin manages subscriptions via /api/v1/admin/subscriptions
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from app.db import collections as c
from app.db.mongodb import database
from app.auth.dependencies import get_current_user
from app.services.subscription_service import activate_subscription

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])


# ──────────────────────────────────────────────────────────────────────────────
# GET /billing/plans
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans():
    """
    Returns the single subscription plan: Treasury Intelligence Pro.
    Public endpoint — no auth required.
    """
    try:
        plan = await database[c.SUBSCRIPTION_PLANS].find_one(
            {"code": "intelligence_tresorerie_pme", "is_active": True}
        )

        if not plan:
            plan = {
                "code": "intelligence_tresorerie_pme",
                "name": "Intelligence Trésorerie PME",
                "description": "Plateforme complète de gestion et d'intelligence de trésorerie pour PME",
                "billing_period": "monthly",
                "price_mad": 299.0,
                "currency": "MAD",
                "trial_days": 14,
                "features": [
                    "upload_intelligent",
                    "memoire_historique",
                    "previsions",
                    "business_intelligence",
                    "decision_center",
                    "notifications",
                    "executive_pdf",
                ],
            }
        
        plan["_id"] = str(plan.get("_id", ""))
        return [plan]
    
    except Exception as e:
        logger.error(f"Error listing plans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/upgrade")
async def upgrade_subscription(current_user=Depends(get_current_user)):
    """Backward-compatible activation alias → POST /subscription/activate."""
    company_id = current_user.get("active_company_id") or current_user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="No active company")
    try:
        await activate_subscription(str(company_id))
        from app.services.subscription_service import get_subscription_status

        status = await get_subscription_status(current_user)
        return {"message": "Abonnement activé", "subscription": status}
    except Exception as e:
        logger.error(f"Upgrade failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upgrade failed") from e
