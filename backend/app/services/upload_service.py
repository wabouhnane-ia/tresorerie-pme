"""Upload pipeline: MongoDB only, production-safe, idempotent!"""

import hashlib
import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import Tuple, Dict

import pandas as pd
from app.utils.bson_utils import ObjectId
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.db import collections as c
from app.db.mongodb import database
from app.services.upload_parser import (
    detect_columns,
    validate_required_columns,
    MissingColumnsError,
    normalize_financial_dataframe,
    dataframe_to_flat_records,
)

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


def _mime_for_ext(ext: str) -> str:
    if ext == ".csv":
        return "text/csv"
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _check_and_create_indexes():
    """Ensure production indexes exist on MongoDB collections."""
    try:
        await database[c.UPLOADS].create_index(
            [("company_id", 1), ("storage.checksum_sha256", 1)],
            unique=True,
            name="company_checksum_unique"
        )
        logger.info("✅ Unique index on (company_id, checksum_sha256) created")
    except OperationFailure as e:
            if e.code == 85:  # IndexOptionsConflict
                logger.info("ℹ️ Index already exists (uploads)")
            else:
                logger.warning(f"Index check (uploads) failed: {e}")
    except Exception as e:
        logger.warning(f"Index check (uploads) failed: {e}")
        
    try:
        await database[c.FINANCIAL_RECORDS].create_index(
            [("company_id", 1), ("date", 1)],
            unique=True,
            name="company_date_unique"
        )
        logger.info("✅ Unique index on (company_id, date) created")
    except OperationFailure as e:
            if e.code == 85:  # IndexOptionsConflict
                logger.info("ℹ️ Index already exists (financial_records)")
            else:
                logger.warning(f"Index check (financial_records) failed: {e}")
    except Exception as e:
        logger.warning(f"Index check (financial_records) failed: {e}")
        
    try:
        await database[c.FORECAST_RUNS].create_index(
            [("company_id", 1)],
            name="company_forecast_run"
        )
        logger.info("✅ Index on (company_id) for forecast_runs created")
    except OperationFailure as e:
            if e.code == 85:  # IndexOptionsConflict
                logger.info("ℹ️ Index already exists (forecast_runs)")
            else:
                logger.warning(f"Index check (forecast_runs) failed: {e}")
    except Exception as e:
        logger.warning(f"Index check (forecast_runs) failed: {e}")


async def _is_forecast_running(company_id: str) -> bool:
    """Check if a forecast run is already in progress for this company."""
    running = await database[c.FORECAST_RUNS].count_documents({
        "company_id": ObjectId(company_id),
        "status": {"$in": ["pending", "running"]}
    })
    return running > 0


async def save_upload(
    *,
    company_id: str,
    user_id: ObjectId,
    original_filename: str,
    file_bytes: bytes,
    extension: str,
) -> Tuple[Dict, bool]:
    """
    Save upload metadata only (NO file written to disk).
    Returns (doc, is_duplicate).
    """
    await _check_and_create_indexes()
    
    checksum = hashlib.sha256(file_bytes).hexdigest()
    upload_id = str(ObjectId())

    doc = {
        "_id": ObjectId(upload_id),
        "company_id": ObjectId(company_id),
        "uploaded_by": user_id,
        "original_filename": original_filename,
        "storage": {
            "mime_type": _mime_for_ext(extension),
            "size_bytes": len(file_bytes),
            "checksum_sha256": checksum,
        },
        "file_type": "cashflow",
        "status": "pending",
        "processing_status": "pending",
        "duplicate_detected": False,
        "records_inserted": 0,
        "records_updated": 0,
        "records_skipped": 0,
        "records_deleted": 0,
        "forecast_retrained": False,
        "parse_report": {},
        "profile": {},
        "created_at": _utcnow(),
    }
    
    try:
        await database[c.UPLOADS].insert_one(doc)
        logger.info(f"✅ New upload saved for company {company_id}")
        return doc, False
    except DuplicateKeyError:
        logger.info(f"ℹ️ Duplicate file detected for company {company_id}")
        existing = await database[c.UPLOADS].find_one({
            "company_id": ObjectId(company_id),
            "storage.checksum_sha256": checksum
        })
        if existing:
            existing["duplicate_detected"] = True
            return existing, True
        return doc, True


async def parse_upload(
    upload_id: str,
    company_id: str,
    file_bytes: bytes = None,
    extension: str = None,
    locale: str = "fr",
) -> dict:
    """
    Main production pipeline: Load -> Detect -> Profile -> Normalize -> Store (intelligent).
    NO file written to disk!
    """
    upload = await database[c.UPLOADS].find_one(
        {
            "_id": ObjectId(upload_id),
            "company_id": ObjectId(company_id),
        }
    )
    if not upload:
        raise ValueError("Upload not found")
        
    # Case 1: Duplicate file
    if upload.get("duplicate_detected"):
        logger.info(f"ℹ️ Skipping processing - duplicate file for company {company_id}")
        await database[c.UPLOADS].update_one(
            {"_id": ObjectId(upload_id)},
            {"$set": {"processing_status": "skipped_duplicate"}}
        )
        return {
            "duplicate": True,
            "message": "File already processed"
        }

    # 1. Load with Pandas from BytesIO
    if file_bytes is None:
        raise ValueError("file_bytes must be provided for in-memory parsing")
    
    from app.services.upload_parser import parse_financial_file

    filename = upload.get("original_filename") or f"data{extension or '.csv'}"
    normalized_df = parse_financial_file(file_bytes, filename, locale=locale)
    records = dataframe_to_flat_records(normalized_df)

    # 4. Store financial_records in MongoDB with upload_id isolation
    records_inserted = 0
    records_updated = 0
    records_skipped = 0
    records_deleted = 0
    data_changed = False

    if records:
        logger.info(f"Processing {len(records)} financial records for company {company_id} with upload_id {upload_id}")
        
        # PHASE 3: Continuous History - Append Only Approach
        # DO NOT delete existing records - append new historical data
        
        # Import continuous history service
        from app.services.continuous_history_service import ContinuousHistoryService
        continuous_service = ContinuousHistoryService()
        
        # Append historical data (never replace)
        append_result = await continuous_service.append_historical_data(
            company_id=company_id,
            upload_id=upload_id,
            df=normalized_df
        )
        
        if append_result["success"]:
            records_inserted = append_result["records_appended"]
            data_changed = records_inserted > 0
            classification = append_result.get("classification", "APPEND_HISTORY")
            append_message = append_result.get("message", "")
            
            logger.info(f"Appended {records_inserted} records to treasury history for company {company_id} - {classification}")
            
            # Handle DUPLICATE_UPLOAD case
            if classification == "DUPLICATE_UPLOAD":
                logger.info(f"DUPLICATE_UPLOAD detected for company {company_id} - all dates already exist")
                # Calculate date range even for duplicates
                if len(normalized_df) > 0:
                    min_date = pd.to_datetime(normalized_df["date"].min()).to_pydatetime()
                    max_date = pd.to_datetime(normalized_df["date"].max()).to_pydatetime()
                    upload_date_range = {
                        "min_date": min_date,
                        "max_date": max_date
                    }
                else:
                    upload_date_range = None
                # Mark upload as duplicate but successful
                await database[c.UPLOADS].update_one(
                    {"_id": ObjectId(upload_id)},
                    {
                        "$set": {
                            "status": "completed",
                            "processing_status": "duplicate_data",
                            "duplicate_detected": True,
                            "records_inserted": 0,
                            "records_skipped": append_result.get("records_skipped", 0),
                            "rows_processed": len(normalized_df),
                            "date_range": upload_date_range,
                            "classification": classification
                        }
                    }
                )
                return {
                    "duplicate": True,
                    "classification": classification,
                    "message": append_message,
                    "records_inserted": 0,
                    "records_skipped": append_result.get("records_skipped", 0),
                    "data_changed": False
                }
            
            # Forecast execution is delegated to the canonical upload lineage pipeline.
            # Keeping retraining out of parse_upload prevents duplicate forecast runs
            # for a single successful upload.
            if data_changed:
                logger.info(
                    "Treasury memory updated for company %s; canonical lineage pipeline will run forecasting once.",
                    company_id,
                )
        else:
            logger.error(f"Failed to append historical data for company {company_id}: {append_result.get('message')}")
            raise ValueError(f"Historical data append failed: {append_result.get('message')}")
        
        # Legacy approach (DEPRECATED in Phase 3) - Commented out
        # This approach replaced historical data, which violates continuous history principle
        # 
        # Extract all dates from new records
        # dates_to_replace = [row["date"] for row in records]
        # 
        # Delete existing records with the same dates (to avoid unique index conflict)
        # delete_result = await database[c.FINANCIAL_RECORDS].delete_many({
        #     "company_id": ObjectId(company_id),
        #     "date": {"$in": dates_to_replace}
        # })
        # records_deleted = delete_result.deleted_count
        # logger.info(f"Deleted {records_deleted} existing records with overlapping dates")
        # 
        # Insert all new records with upload_id
        # docs_to_insert = []
        # for row in records:
        #     doc = {
        #         "company_id": ObjectId(company_id),
        #         "upload_id": ObjectId(upload_id),
        #         "date": row["date"],
        #         "cash_inflow": row["cash_inflow"],
        #         "cash_outflow": row["cash_outflow"],
        #         "net_cashflow": row["net_cashflow"],
        #         "treasury_balance": row["treasury_balance"],
        #         "uploaded_at": _utcnow(),
        #         "created_at": _utcnow(),
        #         "updated_at": _utcnow(),
        #     }
        #     docs_to_insert.append(doc)
        # 
        # if docs_to_insert:
        #     await database[c.FINANCIAL_RECORDS].insert_many(docs_to_insert)
        #     records_inserted = len(docs_to_insert)
        #     data_changed = True
        #     logger.info(f"Inserted {records_inserted} new records with upload_id {upload_id}")

    # 5. Update Upload metadata with detailed tracking
    parse_report = {
        "rows_total": len(normalized_df),
        "rows_valid": len(records),
        "columns_detected": list(normalized_df.columns),
    }

    # === PHASE 1A: Calculate and store historical depth ===
    from app.services.data_maturity_service import DataMaturityService
    from app.services.treasury_profile_service import TreasuryProfileService
    from app.core.config import settings
    maturity_service = DataMaturityService()
    treasury_service = TreasuryProfileService()
    
    # Get the LATEST stored history from financial_records (after we just appended new data!)
    latest_history = await treasury_service._analyze_stored_history(company_id)
    if latest_history:
        historical_months = latest_history["months"]
        # Use tolerance for minimum history check
        forecasting_enabled = (historical_months >= (settings.MIN_HISTORY_MONTHS - settings.HISTORY_TOLERANCE))
        # Determine onboarding status with tolerance
        if historical_months >= (settings.ADVANCED_HISTORY_MONTHS - settings.HISTORY_TOLERANCE):
            onboarding_status = "ADVANCED_READY"
        elif forecasting_enabled:
            onboarding_status = "MINIMUM_READY"
        else:
            onboarding_status = "INSUFFICIENT_HISTORY"
            
        historical_depth = {
            "historical_months": historical_months,
            "is_sufficient": forecasting_enabled,
            "onboarding_status": onboarding_status
        }
        # Determine data maturity with tolerance
        if historical_months >= (settings.EXCELLENT_HISTORY_MONTHS - settings.HISTORY_TOLERANCE):
            maturity_level = "EXCELLENT"
        elif historical_months >= (settings.ADVANCED_HISTORY_MONTHS - settings.HISTORY_TOLERANCE):
            maturity_level = "GOOD"
        else:
            maturity_level = "MEDIUM"
            
        data_analysis = {
            "data_maturity": maturity_level,
            "forecasting_enabled": forecasting_enabled,
            "historical_depth": historical_depth,
            "onboarding_status": onboarding_status
        }
    else:
        # Initial mode: calculate from new file
        data_analysis = maturity_service.analyze_dataset(normalized_df)
        historical_depth = data_analysis.get("historical_depth", {})
        onboarding_status = data_analysis.get("onboarding_status", "INSUFFICIENT_HISTORY")
        forecasting_enabled = data_analysis.get("forecasting_enabled", False)

    # Calculate date range from normalized_df
    if len(normalized_df) > 0:
        min_date = pd.to_datetime(normalized_df["date"].min()).to_pydatetime()
        max_date = pd.to_datetime(normalized_df["date"].max()).to_pydatetime()
        upload_date_range = {
            "min_date": min_date,
            "max_date": max_date
        }
    else:
        upload_date_range = None

    await database[c.UPLOADS].update_one(
        {"_id": ObjectId(upload_id)},
        {
            "$set": {
                "status": "parsed",
                "processing_status": "completed",
                "parse_report": parse_report,
                "records_inserted": records_inserted,
                "records_updated": records_updated,
                "records_skipped": records_skipped,
                "records_deleted": records_deleted,
                "processed_at": _utcnow(),
                "rows_processed": len(normalized_df),
                "date_range": upload_date_range,
                "classification": append_result.get("classification") if "append_result" in locals() else None,
                # === PHASE 1A: Onboarding metadata ===
                "historical_months": historical_depth.get("historical_months", 0),
                "onboarding_status": onboarding_status,
                "forecasting_enabled": forecasting_enabled,
                "data_maturity": data_analysis.get("data_maturity", "POOR"),
                "historical_depth": historical_depth,
            }
        },
    )

    # 6. Forecast retrain status for frontend
    # The actual forecast runs in the background via upload_lineage_service
    forecast_retrained = data_changed and forecasting_enabled
    
    if forecast_retrained:
        # Update upload document immediately to show forecast is being updated
        await database[c.UPLOADS].update_one(
            {"_id": ObjectId(upload_id)},
            {"$set": {"forecast_retrained": True}}
        )
        logger.info(f"✅ Forecasting enabled and data changed - marking forecast as updated for company {company_id}")
    elif data_changed and not forecasting_enabled:
        logger.info(f"ℹ️ Data changed but forecasting disabled due to insufficient historical depth for company {company_id}")

    # 7. Treasury Profile Update (PHASE 3) - Handled in continuous history service
    # Legacy treasury profile update removed - now handled in Phase 3 upload processing
    
    return {
        "duplicate": False,
        "classification": append_result.get("classification", "APPEND_HISTORY") if 'append_result' in locals() else "UNKNOWN",
        "append_message": append_result.get("message", "") if 'append_result' in locals() else "",
        "parse_report": parse_report,
        "records_inserted": records_inserted,
        "records_updated": records_updated,
        "records_skipped": records_skipped,
        "records_deleted": records_deleted,
        "data_changed": data_changed,
        "forecast_retrained": forecast_retrained,
        # === PHASE 1A: Onboarding information ===
        "historical_months": historical_depth.get("historical_months", 0),
        "onboarding_status": onboarding_status,
        "forecasting_enabled": forecasting_enabled,
        "onboarding_message": data_analysis.get("onboarding_message", {}),
    }
