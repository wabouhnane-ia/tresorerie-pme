"""
Upload API — Financial data ingestion.

Quota enforcement is delegated entirely to subscription_service.
Never put billing logic here.
"""

import logging
import os

from app.utils.bson_utils import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request

from app.auth.dependencies import get_current_user
from app.core.locale import resolve_locale
from app.db import collections as c
from app.db.mongodb import database
from app.services import audit_service, upload_service
from app.services.dataset_dedup_service import process_upload_deduplication
from app.services.subscription_service import can_upload, increment_upload_usage
from app.services.upload_lineage_service import process_upload_pipeline, get_upload_lineage
from app.services.upload_parser import MissingColumnsError
from app.services.treasury_profile_service import TreasuryProfileService

router = APIRouter(prefix="/upload", tags=["Uploads"])

logger = logging.getLogger(__name__)

# Initialize treasury profile service
treasury_service = TreasuryProfileService()


@router.get("/requirements")
async def get_upload_requirements():
    """
    Get treasury upload requirements for frontend display.
    
    Returns requirements before user uploads file.
    """
    try:
        requirements = await treasury_service.get_upload_requirements()
        return {
            "success": True,
            "requirements": requirements.dict()
        }
    except Exception as e:
        logger.error(f"Failed to get upload requirements: {e}")
        raise HTTPException(status_code=500, detail="Failed to get upload requirements")


@router.post("/validate")
async def validate_upload_structure(
    file: UploadFile = File(...),
    locale: str = Form("fr"),
    current_user=Depends(get_current_user),
):
    """
    Pre-upload validation endpoint.
    
    Analyzes file structure and historical depth before accepting upload.
    """
    company_id = current_user.get("active_company_id") or current_user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="User has no company")

    # File validation
    allowed_exts = [".csv", ".xlsx", ".xls", ".pdf"]
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail="Invalid file format (.csv, .xlsx, .xls, .pdf only)",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        from app.services.upload_parser import parse_financial_file

        df = parse_financial_file(content, file.filename or f"data{ext}", locale=locale)
        
        # Validate structure and requirements
        validation_result = await treasury_service.validate_upload_structure(company_id, df)
        
        # Check chronological continuity for subsequent uploads
        continuity_result = await treasury_service.validate_chronological_continuity(company_id, df)
        
        return {
            "success": True,
            "validation": validation_result.dict(),
            "continuity": continuity_result.dict(),
            "can_proceed": validation_result.is_valid and continuity_result.is_continuous
        }
        
    except Exception as e:
        logger.error(f"Upload validation failed: {e}")
        return {
            "success": False,
            "validation": {
                "is_valid": False,
                "business_messages": [f"File analysis failed: {str(e)}"]
            },
            "can_proceed": False
        }


@router.post("/financial-data")
async def upload_financial_data(
    file: UploadFile = File(...),
    locale: str = Form("fr"),
    current_user=Depends(get_current_user),
    request: Request = None,
):
    company_id = current_user.get("active_company_id") or current_user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="User has no company")

    # ── File validation ───────────────────────────────────────────────────────
    allowed_exts = [".csv", ".xlsx", ".xls", ".pdf"]
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail="Invalid file format (.csv, .xlsx, .xls, .pdf only)",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # ── STEP 2-5: Process deduplication ──────────────────────────────────────
    try:
        file_hash, dataset_hash, normalized_df, duplicate_upload = await process_upload_deduplication(
            company_id=company_id,
            file_bytes=content,
            extension=ext,
            filename=file.filename,
            locale=locale,
        )
        
    except MissingColumnsError as exc:
        detail = {
                "success": False,
                "error": "Missing required columns",
                "message": "The uploaded dataset does not comply with the Treasury PME V2.0 schema.",
                "error_code": "MISSING_REQUIRED_COLUMNS",
                "error_type": "column_validation",
                "missing_columns": exc.missing_columns,
                "required_columns": ["date", "treasury_balance", "cash_inflow", "cash_outflow",
                                    "scheduled_receipts", "overdue_receipts", "scheduled_payments",
                                    "overdue_payments"],
            }
        if getattr(exc, "suggestions", None):
            detail["suggested_mappings"] = exc.suggestions

        raise HTTPException(status_code=400, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400, 
            detail={
                "error_code": "FILE_PARSE_ERROR",
                "error_type": "file_processing",
                "success": False,
                "message": f"Cannot parse file: {str(exc)}"
            }
        ) from exc

    # ── PHASE 3: Treasury Profile Validation ─────────────────────────────────
    try:
        # Validate treasury requirements and continuity
        validation_result = await treasury_service.validate_upload_structure(company_id, normalized_df)
        continuity_result = await treasury_service.validate_chronological_continuity(company_id, normalized_df)
        
        # Reject only blocking issues (structure, daily frequency). Partial history is allowed:
        # onboarding_status / forecasting_enabled are set after parse (upload_service).
        is_structurally_valid = len(validation_result.missing_required_columns) == 0
        if not is_structurally_valid:
            missing = validation_result.missing_required_columns
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "MISSING_REQUIRED_COLUMNS",
                    "error_type": "column_validation",
                    "success": False,
                    "message": (
                        f"Colonnes obligatoires manquantes : {', '.join(missing)}. "
                        f"Attendu : date, treasury_balance (solde de trésorerie), cash_inflow (encaissements), "
                        f"cash_outflow (décaissements), scheduled_receipts (encaissements planifiés), "
                        f"overdue_receipts (encaissements en retard), scheduled_payments (paiements planifiés), "
                        f"overdue_payments (paiements en retard)."
                    ),
                    "missing_columns": missing,
                    "required_columns": treasury_service.REQUIRED_COLUMNS,
                    "detected_columns": validation_result.detected_columns,
                },
            )

        if not validation_result.is_daily_data:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "NON_DAILY_DATA",
                    "error_type": "treasury_validation",
                    "success": False,
                    "message": (
                        ". ".join(validation_result.business_messages)
                        if validation_result.business_messages
                        else "Les données de trésorerie doivent être journalières (une ligne par jour)."
                    ),
                    "detected_frequency": validation_result.daily_frequency,
                    "coverage_rate": validation_result.daily_coverage_rate,
                    "business_messages": validation_result.business_messages,
                },
            )

        if not validation_result.meets_minimum_requirement:
            logger.info(
                "Upload avec historique partiel accepté pour %s : %.1f mois (minimum prévision : %s)",
                company_id,
                validation_result.detected_months,
                treasury_service.MINIMUM_HISTORY_MONTHS,
            )
        
        # Check chronological continuity for subsequent uploads
        if not continuity_result.is_continuous:
            error_detail = {
                "error_code": "CONTINUITY_ERROR",
                "error_type": "chronological_continuity",
                "success": False,
                "message": ". ".join(continuity_result.messages) if continuity_result.messages else "Chronological continuity error"
            }
            
            if continuity_result.gap_detected:
                error_detail.update({
                    "error_code": "CONTINUITY_GAP",
                    "message": f"Expected next period: {continuity_result.expected_start_date.strftime('%Y-%m') if continuity_result.expected_start_date else 'unknown'}. Received: {continuity_result.received_start_date.strftime('%Y-%m') if continuity_result.received_start_date else 'unknown'}",
                    "gap_days": continuity_result.gap_days,
                    "expected_start": continuity_result.expected_start_date.isoformat() if continuity_result.expected_start_date else None,
                    "received_start": continuity_result.received_start_date.isoformat() if continuity_result.received_start_date else None
                })
            elif continuity_result.overlap_detected:
                error_detail.update({
                    "error_code": "CONTINUITY_OVERLAP",
                    "message": f"Data overlap detected. New data starts {continuity_result.overlap_days} days before expected date.",
                    "overlap_days": continuity_result.overlap_days
                })
            
            raise HTTPException(status_code=400, detail=error_detail)
            
        logger.info(f"Treasury validation passed for company {company_id}: {validation_result.detected_months:.1f} months, {validation_result.history_level.value}")
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as exc:
        logger.error(f"Treasury validation failed for company {company_id}: {exc}")
        raise HTTPException(status_code=400, detail=f"Treasury validation error: {exc}") from exc

    # ── STEP 5: Handle duplicate detection ───────────────────────────────────
    if duplicate_upload:
        # Audit duplicate detection
        await audit_service.log_upload(
            action="duplicate_detected",
            upload_id=str(duplicate_upload["_id"]),
            user_id=str(current_user["_id"]),
            company_id=company_id,
            filename=file.filename,
            status="warning",
            details={
                "original_upload_id": str(duplicate_upload["_id"]),
                "original_filename": duplicate_upload.get("original_filename"),
                "dataset_hash": dataset_hash
            },
            request=request
        )
        
        # Return structured duplicate response
        return {
            "success": False,
            "error_code": "DUPLICATE_DATASET",
            "error_type": "duplicate_detection",
            "message": "This dataset has already been uploaded.",
            "duplicate_detected": True,
            "existing_upload": {
                "upload_id": str(duplicate_upload["_id"]),
                "filename": duplicate_upload.get("original_filename"),
                "upload_date": duplicate_upload.get("created_at")
            },
            # Legacy fields for backward compatibility
            "existing_upload_id": str(duplicate_upload["_id"]),
            "upload_id": str(duplicate_upload["_id"]),
            "duplicate": True
        }

    # ── STEP 6: Not a duplicate - check quota and proceed ────────────────────
    allowed, reason = await can_upload(current_user)
    if not allowed:
        raise HTTPException(
            status_code=403, 
            detail={
                "error_code": "QUOTA_EXCEEDED",
                "error_type": "subscription_expired",
                "success": False,
                "message": reason or "Subscription required.",
                "quota_reason": reason
            }
        )

    # ── STEP 7: Save upload metadata with hashes ─────────────────────────────
    doc, is_duplicate = await upload_service.save_upload(
        company_id=company_id,
        user_id=current_user["_id"],
        original_filename=file.filename,
        file_bytes=content,
        extension=ext,
    )

    # Update the upload document with deduplication hashes
    await database[c.UPLOADS].update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "file_hash": file_hash,
                "dataset_hash": dataset_hash,
                "is_duplicate": False,
                "locale": locale,
            }
        },
    )
    
    # Audit upload started
    await audit_service.log_upload(
        action="upload_started",
        upload_id=str(doc["_id"]),
        user_id=str(current_user["_id"]),
        company_id=company_id,
        filename=file.filename,
        status="success",
        details={
            "file_size_bytes": len(content),
                "file_extension": ext,
                "file_hash": file_hash,
                "dataset_hash": dataset_hash,
                "locale": locale,
            },
            request=request
        )

    # Legacy duplicate check from upload_service (file-based)
    if is_duplicate:
        return {
            "message": "File already processed",
            "duplicate": True,
            "upload_id": str(doc["_id"]),
        }

    # ── Parse and store financial records ────────────────────────────────────
    try:
        parse_result = await upload_service.parse_upload(
            str(doc["_id"]),
            company_id,
            file_bytes=content,
            extension=ext,
            locale=locale,
        )

        if parse_result.get("duplicate"):
            return {
                "message": parse_result["message"],
                "duplicate": True,
                "upload_id": str(doc["_id"]),
                **parse_result
            }

    except MissingColumnsError as exc:
        await database[c.UPLOADS].update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": "failed", "error": str(exc)}},
        )
        
        # Audit upload failure
        await audit_service.log_upload(
            action="upload_failed",
            upload_id=str(doc["_id"]),
            user_id=str(current_user["_id"]),
            company_id=company_id,
            filename=file.filename,
            status="failed",
            error_message=str(exc),
            details={
                "error_type": "missing_columns",
                "missing_columns": exc.missing_columns
            },
            request=request
        )
        
        detail = {
            "success": False,
            "error": "Missing required columns",
            "message": "The uploaded dataset does not comply with the Treasury PME V2.0 schema.",
            "error_code": "MISSING_REQUIRED_COLUMNS",
            "error_type": "column_validation",
            "missing_columns": exc.missing_columns,
            "required_columns": ["date", "treasury_balance", "cash_inflow", "cash_outflow",
                                "scheduled_receipts", "overdue_receipts", "scheduled_payments",
                                "overdue_payments"],
        }
        if getattr(exc, "suggestions", None):
            detail["suggested_mappings"] = exc.suggestions

        raise HTTPException(status_code=400, detail=detail) from exc

    except ValueError as exc:
        # Audit upload failure
        await audit_service.log_upload(
            action="upload_failed",
            upload_id=str(doc["_id"]),
            user_id=str(current_user["_id"]),
            company_id=company_id,
            filename=file.filename,
            status="failed",
            error_message=str(exc),
            details={"error_type": "value_error"},
            request=request
        )
        
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        await database[c.UPLOADS].update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": "failed", "error": str(exc)}},
        )
        
        # Audit upload failure
        await audit_service.log_upload(
            action="upload_failed",
            upload_id=str(doc["_id"]),
            user_id=str(current_user["_id"]),
            company_id=company_id,
            filename=file.filename,
            status="failed",
            error_message=str(exc),
            details={"error_type": "general_exception"},
            request=request
        )
        
        raise HTTPException(status_code=400, detail=f"Cannot parse file: {exc}") from exc

    # ── PHASE 3: Update Treasury Profile ─────────────────────────────────────
    try:
        # Check if this is first upload or subsequent upload
        existing_profile = await treasury_service.get_company_treasury_profile(company_id)
        
        upload_metadata = {
            "upload_id": str(doc["_id"]),
            "filename": file.filename,
            "rows_processed": parse_result.get("rows_processed", 0)
        }
        
        if existing_profile:
            # Update existing profile with new historical data
            treasury_profile = await treasury_service.update_treasury_profile(
                company_id, normalized_df, upload_metadata
            )
            logger.info(f"Updated treasury profile for company {company_id}: {treasury_profile.total_uploads} uploads, {treasury_profile.historical_months:.1f} months")
        else:
            # Create initial treasury profile
            treasury_profile = await treasury_service.create_treasury_profile(
                company_id, normalized_df, upload_metadata
            )
            logger.info(f"Created treasury profile for company {company_id}: {treasury_profile.historical_months:.1f} months, {treasury_profile.history_level.value}")
        
        # Update upload document with treasury profile information
        await database[c.UPLOADS].update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "treasury_profile_updated": True,
                    "historical_months": treasury_profile.historical_months,
                    "history_level": treasury_profile.history_level.value,
                    "total_company_uploads": treasury_profile.total_uploads
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to update treasury profile for company {company_id}: {e}")
        # Don't fail the upload if profile update fails, but log it
        await database[c.UPLOADS].update_one(
            {"_id": doc["_id"]},
            {"$set": {"treasury_profile_error": str(e)}}
        )

    # ── Increment usage counter (after successful parse) ──────────────────────
    await increment_upload_usage(str(current_user["_id"]))

    # ── Process analytical pipeline (lineage & traceability) ──────────────────
    try:
        # Extract DataFrame statistics for quality analysis
        df_stats = {
            "rows": parse_result.get("rows_processed", 0),
            "columns": len(normalized_df.columns) if normalized_df is not None else 0,
            "missing_percentage": 0,  # Will be calculated in quality service
            "has_required_columns": True,  # Already validated by parser
            "date_range": parse_result.get("date_range"),
        }
        
        # Process the complete analytical pipeline asynchronously
        import asyncio
        pipeline_task = asyncio.create_task(
            process_upload_pipeline(
                upload_id=str(doc["_id"]),
                company_id=company_id,
                df_stats=df_stats,
                normalized_df=normalized_df
            )
        )
        
        # Don't wait for pipeline completion - it runs in background
        logger.info(f"Started analytical pipeline for upload {doc['_id']}")
        
    except Exception as e:
        logger.error(f"Failed to start analytical pipeline for upload {doc['_id']}: {e}")
        # Don't fail the upload if pipeline fails to start

    # ── Audit log upload completion ──────────────────────────────────────────
    await audit_service.log_upload(
        action="upload_completed",
        upload_id=str(doc["_id"]),
        user_id=str(current_user["_id"]),
        company_id=company_id,
        filename=file.filename,
        status="success",
        details={
            "rows_processed": parse_result.get("rows_processed", 0),
            "pipeline_started": True,
            "has_lineage": True
        },
        request=request
    )

    # Get total records count from financial_records
    total_records = await database[c.FINANCIAL_RECORDS].count_documents({
        "company_id": ObjectId(company_id)
    })

    return {
        "message": "Financial file uploaded and parsed",
        "upload_id": str(doc["_id"]),
        "pipeline_started": True,
        "records_appended": parse_result.get("records_inserted", 0),
        "records_updated": parse_result.get("records_updated", 0),
        "records_skipped": parse_result.get("records_skipped", 0),
        "total_records": total_records,
        "forecast_retrained": parse_result.get("forecast_retrained", False),
        "historical_months": parse_result.get("historical_months", 0),
        "onboarding_status": parse_result.get("onboarding_status"),
        "forecasting_enabled": parse_result.get("forecasting_enabled"),
        "classification": parse_result.get("classification"),
        **parse_result,
    }


@router.get("/onboarding-status")
async def get_onboarding_status(
    current_user=Depends(get_current_user),
    locale: str = Depends(resolve_locale),
):
    """Get onboarding status for the current company."""
    company_id = current_user.get("active_company_id") or current_user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="No company")

    # Get latest upload to check onboarding status
    latest_upload = await database[c.UPLOADS].find_one(
        {"company_id": ObjectId(company_id)},
        sort=[("created_at", -1)]
    )

    if not latest_upload:
        return {
            "has_uploads": False,
            "onboarding_status": "NO_DATA",
            "historical_months": 0,
            "forecasting_enabled": False,
            "message": {
                "title": {
                    "fr": "Aucune donnée importée",
                    "en": "No data uploaded",
                    "ar": "لم يتم رفع أي بيانات",
                }.get(locale, "Aucune donnée importée"),
                "message": {
                    "fr": "Importez votre premier jeu de données financières pour démarrer l'intégration de l'intelligence trésorerie.",
                    "en": "Upload your first financial dataset to begin treasury intelligence onboarding.",
                    "ar": "ارفع أول مجموعة بيانات مالية لبدء إعداد ذكاء الخزينة.",
                }.get(locale, "Importez votre premier jeu de données financières pour démarrer l'intégration de l'intelligence trésorerie."),
                "type": "info"
            }
        }

    # Extract onboarding information
    historical_months = latest_upload.get("historical_months", 0)
    onboarding_status = latest_upload.get("onboarding_status", "INSUFFICIENT_HISTORY")
    forecasting_enabled = latest_upload.get("forecasting_enabled", False)
    
    # Generate message using historical depth service
    from app.services.historical_depth_service import HistoricalDepthService
    depth_service = HistoricalDepthService()
    
    # Create a mock depth result for message generation
    depth_result = {
        "historical_months": historical_months,
        "onboarding_status": onboarding_status,
        "months_needed": max(0, depth_service.MINIMUM_MONTHS - historical_months)
    }
    
    message = depth_service.get_onboarding_message(depth_result, locale=locale)

    return {
        "has_uploads": True,
        "onboarding_status": onboarding_status,
        "historical_months": historical_months,
        "minimum_required": depth_service.MINIMUM_MONTHS,
        "recommended_months": depth_service.RECOMMENDED_MONTHS,
        "forecasting_enabled": forecasting_enabled,
        "message": message,
        "upload_date": latest_upload.get("created_at"),
    }


@router.get("/treasury-profile")
async def get_treasury_profile(current_user=Depends(get_current_user)):
    """Get treasury profile for the current company."""
    company_id = current_user.get("active_company_id") or current_user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="No company")

    profile = await treasury_service.get_company_treasury_profile(company_id)
    
    if not profile:
        return {
            "exists": False,
            "profile": None
        }
    
    # Ensure fields exist (for existing profiles without them)
    profile_dict = profile.dict()
    if "forecasting_enabled" not in profile_dict or profile_dict["forecasting_enabled"] is None:
        profile_dict["forecasting_enabled"] = profile_dict["historical_months"] >= 24
    if "data_maturity" not in profile_dict or profile_dict["data_maturity"] is None:
        months = profile_dict["historical_months"]
        if months < 24:
            profile_dict["data_maturity"] = "low"
        elif months < 36:
            profile_dict["data_maturity"] = "medium"
        elif months < 48:
            profile_dict["data_maturity"] = "good"
        else:
            profile_dict["data_maturity"] = "optimal"
    
    return {
        "exists": True,
        "profile": profile_dict
    }


@router.get("/list")
async def list_uploads(current_user=Depends(get_current_user)):
    company_id = current_user.get("active_company_id") or current_user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="No company")

    # Get total upload count first
    total_uploads = await database[c.UPLOADS].count_documents({"company_id": ObjectId(company_id)})

    cursor = (
        database[c.UPLOADS]
        .find({"company_id": ObjectId(company_id)})
        .sort("created_at", -1)
        .limit(50)
    )

    items = []
    index = 0
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["company_id"] = str(doc["company_id"])
        if doc.get("uploaded_by"):
            doc["uploaded_by"] = str(doc["uploaded_by"])
        if doc.get("data_quality_report_id"):
            doc["data_quality_report_id"] = str(doc["data_quality_report_id"])
        if doc.get("latest_forecast_run_id"):
            doc["latest_forecast_run_id"] = str(doc["latest_forecast_run_id"])
        if doc.get("latest_risk_assessment_id"):
            doc["latest_risk_assessment_id"] = str(doc["latest_risk_assessment_id"])
        
        # Calculate total_company_uploads for this upload
        doc["total_company_uploads"] = total_uploads - index
        index += 1
        
        # Convert datetime fields to ISO strings for proper JSON serialization
        if doc.get("created_at"):
            doc["created_at"] = doc["created_at"].isoformat()
        if doc.get("processed_at"):
            doc["processed_at"] = doc["processed_at"].isoformat()
        if doc.get("date_range"):
            if doc["date_range"].get("min_date"):
                doc["date_range"]["min_date"] = doc["date_range"]["min_date"].isoformat()
            if doc["date_range"].get("max_date"):
                doc["date_range"]["max_date"] = doc["date_range"]["max_date"].isoformat()
        items.append(doc)
    return items


@router.get("/lineage/{upload_id}")
async def get_upload_lineage_endpoint(
    upload_id: str,
    current_user=Depends(get_current_user)
):
    """
    Get complete analytical lineage for an upload.
    
    Returns the full traceability chain:
    upload → data_quality_report → forecast_run → risk_assessment → recommendations
    """
    company_id = current_user.get("active_company_id") or current_user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="No company")

    try:
        # Verify upload belongs to user's company
        upload = await database[c.UPLOADS].find_one({
            "_id": ObjectId(upload_id),
            "company_id": ObjectId(company_id)
        })
        
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        lineage = await get_upload_lineage(upload_id)
        return lineage
        
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Failed to get upload lineage for {upload_id}: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error") from exc
