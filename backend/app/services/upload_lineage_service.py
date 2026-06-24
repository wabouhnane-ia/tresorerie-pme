"""Upload Lineage & Analytical Traceability Service.

Provides complete traceability from upload through data quality, forecasting,
risk assessment, and recommendations. Each upload becomes a central tracking
entity with links to all derived analytical artifacts.

Architecture:
  upload → data_quality_report → forecast_run → risk_assessment → recommendations → ai_insights
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd

from app.utils.bson_utils import ObjectId

from app.db import collections as c
from app.db.mongodb import database
from app.services import forecast_db_service
from app.services.data_maturity_service import DataMaturityService
from app.services.recommendation_service import create_recommendations
from app.services.risk_service import create_assessment

logger = logging.getLogger(__name__)


def _convert_numpy_types(obj):
    """Convert numpy types to native Python types for MongoDB compatibility."""
    if isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, pd.Series):
        return _convert_numpy_types(obj.to_dict())
    elif isinstance(obj, dict):
        return {k: _convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_types(item) for item in obj]
    else:
        return obj


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────────────────────
# Core lineage tracking functions
# ──────────────────────────────────────────────────────────────────────────────

async def create_data_quality_report(
    upload_id: str,
    company_id: str,
    df_stats: Dict[str, Any],
    normalized_df = None
) -> str:
    """
    Create a data quality report linked to an upload.
    
    Args:
        upload_id: Upload document ID
        company_id: Company ID
        df_stats: DataFrame statistics and quality metrics
        normalized_df: Normalized financial DataFrame
        
    Returns:
        Data quality report ID
    """
    try:
        import pandas as pd
        from app.services.calendar_enrichment_service import CalendarEnrichmentService
        from app.lstm.data_preparation import LSTMDataPreparation
        
        # Initialize report with base stats
        report_data = {
            "dataset_version": "2.0",
            "total_rows": df_stats.get("rows", 0),
            "missing_values": {},
            "duplicate_rows": 0,
            "business_days": 0,
            "holidays": 0,
            "ramadan_days": 0,
            "generated_feature_count": 0,
            "forecast_ready": True,
            "warnings": [],
            **df_stats
        }
        
        if normalized_df is not None:
            # Calculate missing values
            missing = normalized_df.isnull().sum().to_dict()
            report_data["missing_values"] = missing
            
            # Calculate duplicate dates
            if "date" in normalized_df.columns:
                duplicate_count = normalized_df.duplicated(subset=["date"]).sum()
                report_data["duplicate_rows"] = duplicate_count
                if duplicate_count > 0:
                    report_data["warnings"].append(f"{duplicate_count} duplicate dates found")
            
            # Enrich with calendar features
            calendar_service = CalendarEnrichmentService()
            enriched_df = calendar_service.enrich_calendar_features(normalized_df)
            
            # Calculate calendar metrics
            if "is_business_day" in enriched_df.columns:
                report_data["business_days"] = int(enriched_df["is_business_day"].sum())
            if "is_holiday" in enriched_df.columns:
                report_data["holidays"] = int(enriched_df["is_holiday"].sum())
            if "is_ramadan" in enriched_df.columns:
                report_data["ramadan_days"] = int(enriched_df["is_ramadan"].sum())
            
            # Calculate feature metadata
            lstm_prep = LSTMDataPreparation()
            feature_metadata = lstm_prep.get_feature_metadata(enriched_df)
            report_data["generated_feature_count"] = feature_metadata.get("feature_count", 0)
        
        # Calculate quality score
        quality_score = _calculate_quality_score(df_stats, None)
        
        # Convert numpy types in report_data
        report_data = _convert_numpy_types(report_data)
        
        quality_report = {
            "upload_id": ObjectId(upload_id),
            "company_id": ObjectId(company_id),
            "created_at": _utcnow(),
            "statistics": report_data,
            "quality_score": quality_score,
        }
        
        result = await database[c.DATA_QUALITY_REPORTS].insert_one(quality_report)
        report_id = str(result.inserted_id)
        
        logger.info(f"Created data quality report {report_id} for upload {upload_id}")
        return report_id
        
    except Exception as e:
        logger.error(f"Failed to create data quality report for upload {upload_id}: {e}")
        raise


async def update_upload_lineage(
    upload_id: str,
    **updates
) -> None:
    """
    Update upload document with lineage tracking fields.
    
    Args:
        upload_id: Upload document ID
        **updates: Fields to update (data_quality_report_id, latest_forecast_run_id, etc.)
    """
    try:
        await database[c.UPLOADS].update_one(
            {"_id": ObjectId(upload_id)},
            {
                "$set": {
                    **updates,
                    "updated_at": _utcnow(),
                }
            }
        )
        logger.debug(f"Updated upload {upload_id} lineage: {list(updates.keys())}")
        
    except Exception as e:
        logger.error(f"Failed to update upload lineage for {upload_id}: {e}")
        raise


async def process_upload_pipeline(
    upload_id: str,
    company_id: str,
    df_stats: Dict[str, Any],
    normalized_df = None
) -> Dict[str, Any]:
    """
    Process the complete analytical pipeline for an upload.
    
    This is the main orchestration function that creates the full lineage:
    upload → quality → forecast → risk → recommendations
    
    Args:
        upload_id: Upload document ID
        company_id: Company ID
        df_stats: DataFrame statistics
        
    Returns:
        Dictionary with all created artifact IDs
    """
    pipeline_result = {
        "upload_id": upload_id,
        "processing_status": "processing",
        "created_artifacts": {},
        "errors": []
    }
    
    try:
        # Mark upload as processing
        await update_upload_lineage(
            upload_id,
            processing_status="processing"
        )
        
        # Step 1: Create data quality report
        try:
            quality_report_id = await create_data_quality_report(
                upload_id, company_id, df_stats, normalized_df
            )
            pipeline_result["created_artifacts"]["data_quality_report_id"] = quality_report_id
            
            await update_upload_lineage(
                upload_id,
                data_quality_report_id=ObjectId(quality_report_id)
            )
            
        except Exception as e:
            error_msg = f"Data quality analysis failed: {e}"
            pipeline_result["errors"].append(error_msg)
            logger.error(error_msg)
        
        # Step 2: Run forecasting
        try:
            forecast_result = await forecast_db_service.run_prophet_forecast(
                company_id=company_id,
                user_id=None,  # System-generated
                horizon_days=30
            )
            forecast_run_id = forecast_result["forecast_run_id"]
            pipeline_result["created_artifacts"]["forecast_run_id"] = forecast_run_id
            
            # Link forecast run to upload
            await database[c.FORECAST_RUNS].update_one(
                {"_id": ObjectId(forecast_run_id)},
                {
                    "$set": {
                        "upload_id": ObjectId(upload_id),
                        "data_quality_report_id": ObjectId(quality_report_id) if "data_quality_report_id" in pipeline_result["created_artifacts"] else None,
                        "updated_at": _utcnow(),
                    }
                }
            )
            
            await update_upload_lineage(
                upload_id,
                latest_forecast_run_id=ObjectId(forecast_run_id)
            )
            
        except Exception as e:
            error_msg = f"Forecasting failed: {e}"
            pipeline_result["errors"].append(error_msg)
            logger.error(error_msg)
        
        # Step 3: Run risk assessment
        try:
            risk_assessment = await create_assessment(
                company_id=company_id,
            )
            risk_assessment_id = str(risk_assessment["_id"])
            pipeline_result["created_artifacts"]["risk_assessment_id"] = risk_assessment_id
            
            # Link risk assessment to upload and forecast
            await database[c.RISK_ASSESSMENTS].update_one(
                {"_id": ObjectId(risk_assessment_id)},
                {
                    "$set": {
                        "upload_id": ObjectId(upload_id),
                        "forecast_run_id": ObjectId(forecast_run_id) if "forecast_run_id" in pipeline_result["created_artifacts"] else None,
                        "updated_at": _utcnow(),
                    }
                }
            )
            
            await update_upload_lineage(
                upload_id,
                latest_risk_assessment_id=ObjectId(risk_assessment_id)
            )
            
        except Exception as e:
            error_msg = f"Risk assessment failed: {e}"
            pipeline_result["errors"].append(error_msg)
            logger.error(error_msg)
        
        # Step 4: Generate recommendations
        try:
            recommendations = await create_recommendations(
                company_id=company_id,
            )
            recommendations_id = recommendations.get("recommendation_id")
            if recommendations_id:
                pipeline_result["created_artifacts"]["recommendations_id"] = recommendations_id
            
        except Exception as e:
            error_msg = f"Recommendations generation failed: {e}"
            pipeline_result["errors"].append(error_msg)
            logger.error(error_msg)
        
        # Determine final status
        if pipeline_result["errors"]:
            pipeline_result["processing_status"] = "completed_with_errors"
        else:
            pipeline_result["processing_status"] = "completed"
        
        # Update final status
        await update_upload_lineage(
            upload_id,
            processing_status=pipeline_result["processing_status"],
            pipeline_completed_at=_utcnow()
        )
        
        logger.info(
            f"Upload pipeline completed for {upload_id}: "
            f"status={pipeline_result['processing_status']}, "
            f"artifacts={len(pipeline_result['created_artifacts'])}, "
            f"errors={len(pipeline_result['errors'])}"
        )
        
    except Exception as e:
        # Mark upload as failed
        pipeline_result["processing_status"] = "failed"
        pipeline_result["errors"].append(f"Pipeline failed: {e}")
        
        await update_upload_lineage(
            upload_id,
            processing_status="failed",
            pipeline_failed_at=_utcnow(),
            pipeline_error=str(e)
        )
        
        logger.error(f"Upload pipeline failed for {upload_id}: {e}")
    
    return pipeline_result


# ──────────────────────────────────────────────────────────────────────────────
# Lineage retrieval functions
# ──────────────────────────────────────────────────────────────────────────────

async def get_upload_lineage(upload_id: str) -> Dict[str, Any]:
    """
    Get complete lineage for an upload.
    
    Args:
        upload_id: Upload document ID
        
    Returns:
        Complete lineage with all linked artifacts
    """
    try:
        # Get upload document
        upload = await database[c.UPLOADS].find_one({"_id": ObjectId(upload_id)})
        if not upload:
            raise ValueError(f"Upload {upload_id} not found")
        
        lineage = {
            "upload_id": upload_id,
            "upload": {
                "_id": str(upload["_id"]),
                "original_filename": upload.get("original_filename"),
                "created_at": upload.get("created_at"),
                "processing_status": upload.get("processing_status"),
                "file_hash": upload.get("file_hash"),
                "dataset_hash": upload.get("dataset_hash"),
            },
            "data_quality_report": None,
            "forecast_run": None,
            "risk_assessment": None,
            "recommendations": None,
        }
        
        # Get data quality report
        if upload.get("data_quality_report_id"):
            quality_report = await database[c.DATA_QUALITY_REPORTS].find_one(
                {"_id": upload["data_quality_report_id"]}
            )
            if quality_report:
                lineage["data_quality_report"] = {
                    "_id": str(quality_report["_id"]),
                    "data_maturity": quality_report.get("data_maturity"),
                    "quality_score": quality_report.get("quality_score"),
                    "created_at": quality_report.get("created_at"),
                }
        
        # Get latest forecast run
        if upload.get("latest_forecast_run_id"):
            forecast_run = await database[c.FORECAST_RUNS].find_one(
                {"_id": upload["latest_forecast_run_id"]}
            )
            if forecast_run:
                lineage["forecast_run"] = {
                    "_id": str(forecast_run["_id"]),
                    "model_type": forecast_run.get("model_type"),
                    "metrics": forecast_run.get("metrics"),
                    "created_at": forecast_run.get("created_at"),
                }
        
        # Get latest risk assessment
        if upload.get("latest_risk_assessment_id"):
            risk_assessment = await database[c.RISK_ASSESSMENTS].find_one(
                {"_id": upload["latest_risk_assessment_id"]}
            )
            if risk_assessment:
                lineage["risk_assessment"] = {
                    "_id": str(risk_assessment["_id"]),
                    "risk_level": risk_assessment.get("risk_level"),
                    "risk_score": risk_assessment.get("risk_score"),
                    "created_at": risk_assessment.get("created_at"),
                }
        
        # Get recommendations (find by company and recent date)
        company_id = upload.get("company_id")
        if company_id:
            recommendations = await database[c.RECOMMENDATIONS].find_one(
                {"company_id": company_id},
                sort=[("created_at", -1)]
            )
            if recommendations:
                lineage["recommendations"] = {
                    "_id": str(recommendations["_id"]),
                    "total_count": recommendations.get("total_count", 0),
                    "critical_count": recommendations.get("critical_count", 0),
                    "created_at": recommendations.get("created_at"),
                }
        
        return lineage
        
    except Exception as e:
        logger.error(f"Failed to get upload lineage for {upload_id}: {e}")
        raise


async def get_latest_forecast(upload_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest forecast run for an upload.
    
    Args:
        upload_id: Upload document ID
        
    Returns:
        Latest forecast run document or None
    """
    try:
        upload = await database[c.UPLOADS].find_one({"_id": ObjectId(upload_id)})
        if not upload or not upload.get("latest_forecast_run_id"):
            return None
        
        forecast_run = await database[c.FORECAST_RUNS].find_one(
            {"_id": upload["latest_forecast_run_id"]}
        )
        
        if forecast_run:
            forecast_run["_id"] = str(forecast_run["_id"])
            return forecast_run
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to get latest forecast for upload {upload_id}: {e}")
        return None


async def get_latest_risk_assessment(upload_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest risk assessment for an upload.
    
    Args:
        upload_id: Upload document ID
        
    Returns:
        Latest risk assessment document or None
    """
    try:
        upload = await database[c.UPLOADS].find_one({"_id": ObjectId(upload_id)})
        if not upload or not upload.get("latest_risk_assessment_id"):
            return None
        
        risk_assessment = await database[c.RISK_ASSESSMENTS].find_one(
            {"_id": upload["latest_risk_assessment_id"]}
        )
        
        if risk_assessment:
            risk_assessment["_id"] = str(risk_assessment["_id"])
            return risk_assessment
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to get latest risk assessment for upload {upload_id}: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────

def _calculate_quality_score(df_stats: Dict[str, Any], maturity_analysis: Dict[str, Any]) -> float:
    """
    Calculate a quality score based on data statistics and maturity.
    
    Args:
        df_stats: DataFrame statistics
        maturity_analysis: Data maturity analysis result
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    try:
        score = 0.0
        
        # Base score from data maturity
        maturity_level = maturity_analysis.get("level", "POOR")
        maturity_scores = {
            "POOR": 0.2,
            "MEDIUM": 0.5,
            "GOOD": 0.7,
            "EXCELLENT": 0.9
        }
        score += maturity_scores.get(maturity_level, 0.2)
        
        # Adjust for missing data percentage
        missing_percentage = df_stats.get("missing_percentage", 0)
        if missing_percentage < 5:
            score += 0.1
        elif missing_percentage > 20:
            score -= 0.1
        
        # Adjust for data consistency
        if df_stats.get("has_required_columns", False):
            score += 0.05
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
        
    except Exception:
        return 0.5  # Default score if calculation fails
