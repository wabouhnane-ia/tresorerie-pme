"""Forecast API using the canonical Mongo-backed forecast pipeline."""

import logging

from app.utils.bson_utils import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.auth.subscription_gate import require_active_subscription
from app.core.locale import resolve_locale
from app.schemas.forecast_schema import TrainRequest
from app.services import forecast_db_service
from app.services.upload_service import _is_forecast_running

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forecast", tags=["forecast"])


def _message(key: str, locale: str) -> str:
    messages = {
        "fr": {
            "no_active_company": "Aucune entreprise active",
            "already_running": "Prévision déjà en cours",
            "updated": "Projections mises à jour",
            "failed": "Échec de la mise à jour des projections",
        },
        "en": {
            "no_active_company": "No active company",
            "already_running": "Forecast already in progress",
            "updated": "Projections updated",
            "failed": "Failed to refresh projections",
        },
        "ar": {
            "no_active_company": "لا توجد شركة نشطة",
            "already_running": "التوقع قيد التنفيذ بالفعل",
            "updated": "تم تحديث التوقعات",
            "failed": "فشل تحديث التوقعات",
        },
    }
    return messages.get(locale, messages["fr"]).get(key, key)


@router.get("/status")
async def forecast_status(
    current_user: dict = Depends(get_current_user),
    _subscription: dict = Depends(require_active_subscription),
):
    """Return whether a forecast run is currently pending/running for the company."""
    company_id = current_user.get("company_id") or current_user.get("active_company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="No active company")

    running = await _is_forecast_running(company_id)
    return {"running": running}


@router.post("/train")
async def train_models(
    request: TrainRequest,
    current_user: dict = Depends(get_current_user),
    _subscription: dict = Depends(require_active_subscription),
    locale: str = Depends(resolve_locale),
):
    """
    Refresh treasury projections for the active company.

    Deprecated legacy path note:
    this endpoint used to execute app.models.ForecastingPipeline directly.
    It now delegates to forecast_db_service so all forecast persistence uses
    the canonical forecast_runs and forecasts write path.
    """
    try:
        company_id = current_user.get("company_id") or current_user.get("active_company_id")
        if not company_id:
            raise HTTPException(status_code=400, detail=_message("no_active_company", locale))

        # Prevent concurrent forecast runs for the same company
        if await _is_forecast_running(company_id):
            raise HTTPException(status_code=409, detail=_message("already_running", locale))

        logger.info("Refreshing projections for company %s", company_id)

        result = await forecast_db_service.run_prophet_forecast(
            company_id=company_id,
            user_id=ObjectId(current_user.get("_id")),
            horizon_days=request.horizon_days,
        )

        return {
            "status": "completed",
            "message": _message("updated", locale),
            "forecast_run_id": result.get("forecast_run_id"),
            "horizon_days": request.horizon_days,
            "points_saved": result.get("points_saved", 0),
        }

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Projection refresh failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=_message("failed", locale)) from exc
