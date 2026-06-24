"""Decision History & Action Tracking API — Sprint 7."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.subscription_gate import require_tenant_subscription
from app.core.locale import resolve_locale
from app.schemas.decision_schema import CreateDecisionSchema, UpdateDecisionStatusSchema
from app.services.decision_service import DECISION_STATUSES, DecisionService

router = APIRouter(prefix="/decisions", tags=["Decision History"])

_service = DecisionService()


@router.get("")
async def list_decisions(
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
    status: str | None = Query(None, description="Filter by status"),
):
    """List all decisions for the active company, grouped by status."""
    if status and status not in DECISION_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {sorted(DECISION_STATUSES)}")
    return await _service.list_decisions(ctx["company_id"], status=status)


@router.get("/history")
async def decision_history_timeline(
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
    limit: int = Query(50, ge=1, le=200),
):
    """Timeline of decisions with status changes and observed impact."""
    return await _service.get_history_timeline(ctx["company_id"], limit=limit)


@router.get("/impact")
async def decision_impact_analytics(
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
):
    """Analytics: total decisions, execution rate, average impact score."""
    return await _service.get_impact_analytics(ctx["company_id"])


@router.get("/pdf-data")
async def decision_pdf_data(
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
    limit: int = Query(10, ge=1, le=50),
):
    """Prepared decision history data for a future Executive PDF section (read-only export)."""
    return await _service.prepare_pdf_data(ctx["company_id"], limit=limit)


@router.post("", status_code=201)
async def create_decision(
    body: CreateDecisionSchema,
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
):
    """Record a new strategic decision."""
    decision = await _service.create_decision(
        ctx["company_id"],
        {**body.model_dump(mode="json"), "locale": locale},
    )
    return {"decision": decision}


@router.patch("/{decision_id}/status")
async def update_decision_status(
    decision_id: str,
    body: UpdateDecisionStatusSchema,
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
):
    """Update decision status. Impact is computed automatically when status becomes completed."""
    try:
        decision = await _service.update_status(
            ctx["company_id"],
            decision_id,
            body.status,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Decision not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"decision": decision}


@router.post("/recompute-impact")
async def recompute_decision_impact(
    ctx: dict = Depends(require_tenant_subscription),
    locale: str = Depends(resolve_locale),
):
    """Recompute impact for all completed decisions."""
    return await _service.recompute_impact(ctx["company_id"])
