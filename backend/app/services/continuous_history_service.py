"""
Continuous History Service for Treasury Platform

Handles historical data appending, validation, and automatic retraining.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from bson import ObjectId

from app.db.mongodb import database
from app.db import collections as c
from app.services.treasury_profile_service import TreasuryProfileService
from app.models.treasury_profile_model import HistoryLevel

logger = logging.getLogger(__name__)


class ContinuousHistoryService:
    """
    Service for managing continuous treasury history and automatic retraining.
    """
    
    def __init__(self):
        self.treasury_service = TreasuryProfileService()
    
    async def append_historical_data(
        self,
        company_id: str,
        upload_id: str,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Append new historical data to existing treasury records.
        
        This is the core function that implements the "DO NOT replace" rule.
        Historical records are always appended, never replaced.
        
        Handles three cases:
        - CASE A: All dates already exist (DUPLICATE_UPLOAD)
        - CASE B: Some dates exist (PARTIAL_OVERLAP - insert only new dates)
        - CASE C: All dates new (APPEND_HISTORY)
        
        Args:
            company_id: Company identifier
            upload_id: Upload document ID
            df: New DataFrame with treasury data
            
        Returns:
            Dictionary with append results and statistics
        """
        try:
            logger.info(f"Starting historical data append for company {company_id}, upload {upload_id}")
            
            # STEP 1: Get existing date range for this company
            existing_dates_pipeline = [
                {"$match": {"company_id": ObjectId(company_id)}},
                {"$group": {
                    "_id": None,
                    "min_date": {"$min": "$date"},
                    "max_date": {"$max": "$date"},
                    "dates": {"$addToSet": "$date"}
                }}
            ]
            
            existing_result = await database[c.FINANCIAL_RECORDS].aggregate(existing_dates_pipeline).to_list(1)
            
            if existing_result:
                existing_dates_set = set(existing_result[0]["dates"])
                existing_min = existing_result[0]["min_date"]
                existing_max = existing_result[0]["max_date"]
                logger.info(f"Found existing records from {existing_min} to {existing_max} ({len(existing_dates_set)} dates)")
            else:
                existing_dates_set = set()
                existing_min = None
                existing_max = None
                logger.info(f"No existing records found for company {company_id}")
            
            # STEP 2: Analyze new data dates
            df_copy = df.copy()
            df_copy['date'] = pd.to_datetime(df_copy['date'])
            new_dates = set(df_copy['date'].dt.to_pydatetime())
            new_min = min(new_dates)
            new_max = max(new_dates)
            
            logger.info(f"New data contains {len(new_dates)} dates from {new_min} to {new_max}")
            
            # STEP 3: Classify upload and filter records
            duplicate_dates = new_dates & existing_dates_set
            unique_new_dates = new_dates - existing_dates_set
            
            upload_classification = None
            
            if len(duplicate_dates) == len(new_dates):
                # CASE A: All dates already exist
                upload_classification = "DUPLICATE_UPLOAD"
                logger.info(f"CASE A: All {len(new_dates)} dates already exist - DUPLICATE_UPLOAD")
                
                return {
                    "success": True,
                    "classification": upload_classification,
                    "records_appended": 0,
                    "records_skipped": len(duplicate_dates),
                    "duplicate_dates_count": len(duplicate_dates),
                    "message": "Dataset already imported. All dates already exist in treasury history.",
                    "existing_records": len(existing_dates_set),
                    "total_records": len(existing_dates_set),
                    "historical_growth": {
                        "previous_days": len(existing_dates_set),
                        "new_days": 0,
                        "total_days": len(existing_dates_set),
                        "total_months": len(existing_dates_set) / 30.44
                    },
                    "treasury_memory_updated": False
                }
            
            elif len(duplicate_dates) > 0:
                # CASE B: Partial overlap - insert only new dates
                upload_classification = "PARTIAL_OVERLAP"
                logger.info(f"CASE B: {len(duplicate_dates)} dates exist, {len(unique_new_dates)} dates are new - PARTIAL_OVERLAP")
            
            else:
                # CASE C: All dates are new
                upload_classification = "APPEND_HISTORY"
                logger.info(f"CASE C: All {len(new_dates)} dates are new - APPEND_HISTORY")
            
            # STEP 4: Prepare records for insertion (only unique new dates)
            records_to_insert = []
            for _, row in df_copy.iterrows():
                row_date = pd.to_datetime(row['date']).to_pydatetime()
                
                # Skip if date already exists
                if row_date in existing_dates_set:
                    continue
                
                record = {
                    "company_id": ObjectId(company_id),
                    "upload_id": ObjectId(upload_id),
                    "date": row_date,
                    "cash_inflow": float(row['cash_inflow']),
                    "cash_outflow": float(row['cash_outflow']),
                    "net_cashflow": float(row['cash_inflow']) - float(row['cash_outflow']),
                    "created_at": datetime.utcnow()
                }
                
                # Add treasury_balance if present
                if 'treasury_balance' in row and pd.notna(row['treasury_balance']):
                    record["treasury_balance"] = float(row['treasury_balance'])
                
                # Add commitment columns if present
                commitment_columns = [
                    'scheduled_receipts', 'overdue_receipts', 
                    'scheduled_payments', 'overdue_payments'
                ]
                for col in commitment_columns:
                    if col in row and pd.notna(row[col]):
                        record[col] = float(row[col])
                    else:
                        record[col] = 0.0
                
                # Add optional enrichment columns
                optional_columns = [
                    'category', 'supplier_name', 'client_name', 'payment_delay',
                    'invoice_count', 'currency', 'region', 'business_unit'
                ]
                
                for col in optional_columns:
                    if col in row and pd.notna(row[col]):
                        record[col] = str(row[col])
                
                records_to_insert.append(record)
            
            # STEP 5: Insert new records (append to history)
            inserted_count = 0
            if records_to_insert:
                try:
                    result = await database[c.FINANCIAL_RECORDS].insert_many(records_to_insert, ordered=False)
                    inserted_count = len(result.inserted_ids)
                    logger.info(f"Successfully appended {inserted_count} new records to treasury history")
                except Exception as insert_error:
                    # Handle any remaining duplicate key errors gracefully
                    if "E11000" in str(insert_error):
                        logger.warning(f"Some duplicate keys detected during insert, but continuing")
                        # Count successful inserts
                        inserted_count = len(records_to_insert) - len(duplicate_dates)
                    else:
                        raise
            
            # STEP 6: Get updated statistics
            total_count = await database[c.FINANCIAL_RECORDS].count_documents({
                "company_id": ObjectId(company_id)
            })
            
            # Calculate date range of complete history
            date_range_pipeline = [
                {"$match": {"company_id": ObjectId(company_id)}},
                {"$group": {
                    "_id": None,
                    "earliest_date": {"$min": "$date"},
                    "latest_date": {"$max": "$date"}
                }}
            ]
            
            date_range_result = await database[c.FINANCIAL_RECORDS].aggregate(date_range_pipeline).to_list(1)
            
            if date_range_result:
                earliest_date = date_range_result[0]["earliest_date"]
                latest_date = date_range_result[0]["latest_date"]
                total_days = (latest_date - earliest_date).days + 1
                total_months = total_days / 30.44
            else:
                earliest_date = latest_date = None
                total_days = total_months = 0
            
            # STEP 7: Generate business-friendly message
            if upload_classification == "PARTIAL_OVERLAP":
                message = f"Historical overlap detected. {inserted_count} new days imported, {len(duplicate_dates)} days already existed."
            else:  # APPEND_HISTORY
                message = f"History successfully extended. {inserted_count} new days imported."
            
            return {
                "success": True,
                "classification": upload_classification,
                "message": message,
                "records_appended": inserted_count,
                "records_skipped": len(duplicate_dates) if duplicate_dates else 0,
                "duplicate_dates_count": len(duplicate_dates) if duplicate_dates else 0,
                "existing_records": len(existing_dates_set),
                "total_records": total_count,
                "historical_growth": {
                    "previous_days": len(existing_dates_set),
                    "new_days": inserted_count,
                    "total_days": total_days,
                    "total_months": total_months
                },
                "date_range": {
                    "earliest_date": earliest_date,
                    "latest_date": latest_date
                },
                "treasury_memory_updated": inserted_count > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to append historical data for company {company_id}: {e}")
            
            # Never expose MongoDB errors to frontend
            error_message = "Failed to process treasury data"
            if "E11000" in str(e) or "duplicate key" in str(e).lower():
                error_message = "Duplicate data detected. Some records already exist in treasury history."
            
            return {
                "success": False,
                "classification": "ERROR",
                "message": error_message,
                "records_appended": 0,
                "treasury_memory_updated": False
            }
    
    async def trigger_automatic_retraining(
        self,
        company_id: str,
        upload_id: str,
        historical_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger automatic retraining after successful historical append.
        
        Args:
            company_id: Company identifier
            upload_id: Upload document ID
            historical_stats: Statistics from historical append
            
        Returns:
            Dictionary with retraining results
        """
        try:
            logger.info(f"Starting automatic retraining for company {company_id} after upload {upload_id}")
            
            # Get updated treasury profile
            profile = await self.treasury_service.get_company_treasury_profile(company_id)
            if not profile:
                logger.warning(f"No treasury profile found for company {company_id}")
                return {"success": False, "error": "No treasury profile found"}
            
            # Check if forecasting is enabled based on history level
            forecasting_enabled = profile.history_level in [
                HistoryLevel.READY, HistoryLevel.ADVANCED, HistoryLevel.OPTIMAL
            ]
            
            if not forecasting_enabled:
                logger.info(f"Forecasting not enabled for company {company_id}: {profile.history_level.value} level")
                return {
                    "success": True,
                    "forecasting_enabled": False,
                    "reason": f"Insufficient history: {profile.history_level.value}",
                    "historical_months": profile.historical_months,
                    "minimum_required": self.treasury_service.MINIMUM_HISTORY_MONTHS
                }
            
            # Prepare retraining data
            retraining_data = {
                "company_id": company_id,
                "upload_id": upload_id,
                "trigger": "automatic_after_upload",
                "historical_stats": historical_stats,
                "profile_stats": {
                    "total_uploads": profile.total_uploads,
                    "historical_months": profile.historical_months,
                    "history_level": profile.history_level.value
                }
            }
            
            # Import and trigger forecasting pipeline
            from app.services.forecast_db_service import retrain_company_forecast
            
            retraining_result = await retrain_company_forecast(company_id)
            
            logger.info(f"Automatic retraining completed for company {company_id}: {retraining_result.get('status', 'unknown')}")
            
            return {
                "success": True,
                "forecasting_enabled": True,
                "retraining_triggered": True,
                "retraining_result": retraining_result,
                "historical_months": profile.historical_months,
                "history_level": profile.history_level.value
            }
            
        except Exception as e:
            logger.error(f"Failed to trigger automatic retraining for company {company_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "retraining_triggered": False
            }
    
    async def validate_historical_continuity_detailed(
        self,
        company_id: str,
        new_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Perform detailed historical continuity validation.
        
        Args:
            company_id: Company identifier
            new_df: New DataFrame to validate
            
        Returns:
            Detailed validation result
        """
        try:
            # Get latest record from existing history
            latest_record = await database[c.FINANCIAL_RECORDS].find_one(
                {"company_id": ObjectId(company_id)},
                sort=[("date", -1)]
            )
            
            if not latest_record:
                # First upload - no continuity to check
                return {
                    "is_continuous": True,
                    "validation_type": "first_upload",
                    "message": "First upload - establishing treasury history baseline"
                }
            
            # Analyze new data
            new_df_copy = new_df.copy()
            new_df_copy['date'] = pd.to_datetime(new_df_copy['date'])
            new_earliest = new_df_copy['date'].min().to_pydatetime()
            new_latest = new_df_copy['date'].max().to_pydatetime()
            
            # Expected continuation date
            expected_next = latest_record["date"] + timedelta(days=1)
            
            # Detailed continuity analysis
            if new_earliest == expected_next:
                continuity_status = "perfect_continuity"
                is_continuous = True
                message = "Perfect chronological continuity"
            elif new_earliest > expected_next:
                gap_days = (new_earliest - expected_next).days
                continuity_status = "gap_detected"
                is_continuous = False
                message = f"Gap detected: {gap_days} days missing between {expected_next.strftime('%Y-%m-%d')} and {new_earliest.strftime('%Y-%m-%d')}"
            elif new_earliest < expected_next:
                overlap_days = (expected_next - new_earliest).days
                continuity_status = "overlap_detected"
                is_continuous = False
                message = f"Overlap detected: {overlap_days} days overlap with existing data"
            else:
                continuity_status = "unknown"
                is_continuous = False
                message = "Unknown continuity status"
            
            return {
                "is_continuous": is_continuous,
                "validation_type": "continuity_check",
                "continuity_status": continuity_status,
                "message": message,
                "details": {
                    "latest_existing_date": latest_record["date"],
                    "expected_next_date": expected_next,
                    "new_data_start": new_earliest,
                    "new_data_end": new_latest,
                    "gap_days": (new_earliest - expected_next).days if new_earliest > expected_next else 0,
                    "overlap_days": (expected_next - new_earliest).days if new_earliest < expected_next else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to validate historical continuity for company {company_id}: {e}")
            return {
                "is_continuous": False,
                "validation_type": "error",
                "message": f"Continuity validation failed: {str(e)}"
            }
    
    async def get_treasury_memory_stats(self, company_id: str) -> Dict[str, Any]:
        """
        Get comprehensive treasury memory statistics.
        
        Args:
            company_id: Company identifier
            
        Returns:
            Dictionary with memory statistics
        """
        try:
            # Get treasury profile
            profile = await self.treasury_service.get_company_treasury_profile(company_id)
            
            # Get record statistics
            stats_pipeline = [
                {"$match": {"company_id": ObjectId(company_id)}},
                {"$group": {
                    "_id": None,
                    "total_records": {"$sum": 1},
                    "earliest_date": {"$min": "$date"},
                    "latest_date": {"$max": "$date"},
                    "total_inflow": {"$sum": "$cash_inflow"},
                    "total_outflow": {"$sum": "$cash_outflow"},
                    "avg_daily_inflow": {"$avg": "$cash_inflow"},
                    "avg_daily_outflow": {"$avg": "$cash_outflow"}
                }}
            ]
            
            stats_result = await database[c.FINANCIAL_RECORDS].aggregate(stats_pipeline).to_list(1)
            
            if not stats_result:
                return {
                    "has_memory": False,
                    "message": "No treasury memory found"
                }
            
            stats = stats_result[0]
            
            # Calculate memory metrics
            total_days = (stats["latest_date"] - stats["earliest_date"]).days + 1
            total_months = total_days / 30.44
            
            # Get upload history
            upload_count = await database[c.UPLOADS].count_documents({
                "company_id": ObjectId(company_id),
                "status": "completed"
            })
            
            return {
                "has_memory": True,
                "treasury_memory": {
                    "total_records": stats["total_records"],
                    "total_days": total_days,
                    "total_months": total_months,
                    "earliest_date": stats["earliest_date"],
                    "latest_date": stats["latest_date"],
                    "upload_count": upload_count
                },
                "financial_summary": {
                    "total_inflow": stats["total_inflow"],
                    "total_outflow": stats["total_outflow"],
                    "net_cashflow": stats["total_inflow"] - stats["total_outflow"],
                    "avg_daily_inflow": stats["avg_daily_inflow"],
                    "avg_daily_outflow": stats["avg_daily_outflow"]
                },
                "profile_info": profile.dict() if profile else None,
                "memory_quality": {
                    "history_level": profile.history_level.value if profile else "unknown",
                    "forecasting_enabled": profile.history_level in [
                        HistoryLevel.READY, HistoryLevel.ADVANCED, HistoryLevel.OPTIMAL
                    ] if profile else False,
                    "data_completeness": min(100, (total_days / (profile.historical_days or 1)) * 100) if profile else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get treasury memory stats for company {company_id}: {e}")
            return {
                "has_memory": False,
                "error": str(e)
            }