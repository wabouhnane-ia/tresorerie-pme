import logging
import re
from urllib.parse import quote

from app.utils.bson_utils import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth.subscription_gate import require_tenant_subscription
from app.core.locale import resolve_locale
from app.db import collections as c
from app.db.mongodb import database
from app.reporting.pdf_report import generate_pdf_report
from app.services import analytics_service
from app.services.business_intelligence_service import BusinessIntelligenceService
from app.services.forecast_db_service import get_forecast_points

router = APIRouter()
logger = logging.getLogger(__name__)


def _message(key: str, locale: str) -> str:
    messages = {
        "fr": {
            "no_data": "Aucune donnée financière disponible. Importez vos données de trésorerie.",
            "bi_failed": "Impossible de générer l'intelligence directionnelle pour cette entreprise.",
            "report_failed": "Échec de la génération du rapport exécutif.",
        },
        "en": {
            "no_data": "No financial data available. Upload your treasury data.",
            "bi_failed": "Unable to generate executive intelligence for this company.",
            "report_failed": "Executive report generation failed.",
        },
        "ar": {
            "no_data": "لا توجد بيانات مالية متاحة. يرجى استيراد بيانات الخزينة.",
            "bi_failed": "تعذر إنشاء الذكاء التنفيذي لهذه الشركة.",
            "report_failed": "فشل إنشاء التقرير التنفيذي.",
        },
    }
    return messages.get(locale, messages["fr"]).get(key, key)


def _slugify_filename(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "-", slug).strip("-").lower()
    return slug[:60] or "entreprise"


async def _get_company_name(company_id: str) -> str:
    company = await database[c.COMPANIES].find_one({"_id": ObjectId(company_id)})
    if not company:
        return "Entreprise"
    return (
        company.get("name")
        or company.get("company_name")
        or company.get("legal_name")
        or "Entreprise"
    )


@router.get("/dashboard/report")
async def generate_report(
    ctx: dict = Depends(require_tenant_subscription),
    language: str = "fr",
):
    """Generate premium executive treasury PDF (BI V3) in specified language."""
    company_id = ctx["company_id"]
    valid_languages = ["fr", "en", "ar"]
    if language not in valid_languages:
        language = "fr"

    try:
        context = await analytics_service.get_treasury_context(company_id)
        if not context:
            raise HTTPException(
                status_code=404,
                detail=_message("no_data", language),
            )

        business_intelligence = await BusinessIntelligenceService().generate(company_id, locale=language)
        if not business_intelligence:
            raise HTTPException(
                status_code=404,
                detail=_message("bi_failed", language),
            )

        company_name = await _get_company_name(company_id)
        kpis = await analytics_service.get_kpis(company_id, locale=language)
        forecast = await get_forecast_points(company_id, limit=30)

        pdf_bytes = generate_pdf_report(
            company_id=company_id,
            kpis=kpis,
            forecast=forecast,
            company_name=company_name,
            business_intelligence=business_intelligence,
            locale=language,
        )

        prefix = {"fr": "rapport-tresorerie-executif", "en": "executive-treasury-report", "ar": "report"}.get(language, "rapport-tresorerie-executif")
        filename = f"{prefix}-{_slugify_filename(company_name)}.pdf"
        
        # Encode filename properly for HTTP headers (supports non-Latin characters)
        encoded_filename = quote(filename)
        content_disposition = f"attachment; filename*=UTF-8''{encoded_filename}; filename=\"{filename.encode('ascii', 'ignore').decode()}\""
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": content_disposition},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Executive PDF report failed for company %s: %s", company_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=_message("report_failed", language)) from e
