"""Access control dependency — blocks expired/cancelled company subscriptions."""

from fastapi import Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.auth.tenant import get_active_company_id, get_tenant_context
from app.services.subscription_service import (
    SUBSCRIPTION_REQUIRED_MESSAGE,
    ensure_subscription_current,
    has_active_access,
    is_super_admin,
)


async def require_active_subscription(
    current_user: dict = Depends(get_current_user),
    company_id: str = Depends(get_active_company_id),
) -> dict:
    """Raise 403 when the active company's subscription does not allow product access."""
    if is_super_admin(current_user):
        return {"user": current_user, "company_id": company_id}

    await ensure_subscription_current(company_id)
    if not await has_active_access(company_id):
        raise HTTPException(
            status_code=403,
            detail={
                "error_type": "subscription_expired",
                "message": SUBSCRIPTION_REQUIRED_MESSAGE,
            },
        )
    return {"user": current_user, "company_id": company_id}


async def require_tenant_subscription(
    ctx: dict = Depends(get_tenant_context),
) -> dict:
    """Tenant context with subscription gate (decisions, notifications, PDF)."""
    user = ctx["user"]
    company_id = ctx["company_id"]
    if is_super_admin(user):
        return ctx

    await ensure_subscription_current(company_id)
    if not await has_active_access(company_id):
        raise HTTPException(
            status_code=403,
            detail={
                "error_type": "subscription_expired",
                "message": SUBSCRIPTION_REQUIRED_MESSAGE,
            },
        )
    return ctx
