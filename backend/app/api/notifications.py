"""Notification Center API — Alert management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.subscription_gate import require_tenant_subscription
from app.core.locale import resolve_locale
from app.schemas.notification_schema import MarkReadSchema
from app.services.notification_service import NotificationService
from app.auth.dependencies import get_current_user


class TestNotificationRequest(BaseModel):
    """Request body for test notification creation."""
    notification_type: str = "warning"
    severity: str = "high"
    title: str = "Notification de test"
    message: str = "Sprint 8 fonctionne correctement ✅"
    metadata: dict | None = None


router = APIRouter(prefix="/notifications", tags=["Notification Center"])

_service = NotificationService()


@router.get("")
async def list_notifications(
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    """List all notifications for the active company, with pagination."""
    result = await _service.list_notifications(
        ctx["company_id"],
        unread_only=False,
        limit=limit,
        skip=skip,
        locale=locale,
    )
    return result


@router.get("/unread")
async def get_unread_notifications(
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
):
    """Get all unread notifications (for notification bell)."""
    result = await _service.get_unread_notifications(ctx["company_id"], locale=locale)
    return result


@router.get("/statistics")
async def notification_statistics(
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
):
    """Get notification statistics (total, unread, critical, etc.)."""
    stats = await _service.get_statistics(ctx["company_id"])
    return stats


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    body: MarkReadSchema,
    ctx: dict = Depends(require_tenant_subscription),
):
    """Mark a specific notification as read/unread."""
    try:
        result = await _service.mark_as_read(ctx["company_id"], notification_id)
        return {"notification": result}
    except LookupError:
        raise HTTPException(status_code=404, detail="Notification not found") from None


@router.patch("/read-all")
async def mark_all_read(ctx: dict = Depends(require_tenant_subscription)):
    """Mark all unread notifications as read."""
    result = await _service.mark_all_as_read(ctx["company_id"])
    return result


@router.post("/test")
async def create_test_notification(
    req: TestNotificationRequest,
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
):
    """
    🧪 TEST ENDPOINT - Create a test notification to validate the Notification Center.
    
    This route creates a test notification with custom values.
    Perfect for validating the UI displays correctly.
    
    **Request Body:**
    - `notification_type`: "warning" (default) | "risk" | "opportunity" | "decision" | "success"
    - `severity`: "low" | "medium" | "high" | "critical" (default: "high")
    - `title`: Custom title
    - `message`: Custom message
    - `metadata`: Optional metadata dict
    
    **Example:**
    ```json
    {
        "notification_type": "risk",
        "severity": "critical",
        "title": "CRITICAL: Runway < 30 jours",
        "message": "Action immédiate requise"
    }
    ```
    """
    result = await _service.create_notification(
        company_id=ctx["company_id"],
        notification_type=req.notification_type,
        severity=req.severity,
        title=req.title,
        message=req.message,
        source="TEST_ENDPOINT",
        metadata={**(req.metadata or {}), "locale": locale}
    )
    
    return {
        "success": True,
        "message": "Test notification created successfully",
        "notification": result
    }


class CreateNotificationRequest(BaseModel):
    notification_type: str
    severity: str
    title: str
    message: str
    metadata: dict | None = None


@router.post("")
async def create_notification_endpoint(
    req: CreateNotificationRequest,
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
):
    """Create a notification (production-safe).

    This endpoint is intended for internal UI flows to persist a notification
    for the active company. Caller must be authenticated and tenant-scoped.
    """
    result = await _service.create_notification(
        company_id=ctx["company_id"],
        notification_type=req.notification_type,
        severity=req.severity,
        title=req.title,
        message=req.message,
        source="UI",
        metadata={**(req.metadata or {}), "locale": locale},
    )

    return {
        "success": True,
        "notification": result,
    }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    ctx: dict = Depends(require_tenant_subscription),
):
    """Delete a notification."""
    try:
        await _service.delete_notification(ctx["company_id"], notification_id)
        return {"deleted": True}
    except LookupError:
        raise HTTPException(status_code=404, detail="Notification not found") from None
