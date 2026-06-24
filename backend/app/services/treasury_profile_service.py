"""
Treasury Profile Service for Continuous Treasury History Platform

Manages company treasury profiles, validation, and historical continuity.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from bson import ObjectId

from app.db.mongodb import database
from app.db import collections as c
from app.models.treasury_profile_model import (
    TreasuryProfileModel,
    TreasuryRequirementsModel,
    UploadValidationResult,
    ContinuityValidationResult,
    HistoryLevel
)
from app.services.daily_data_validator import DailyDataValidator, DatasetFrequency
from app.core.config import settings

logger = logging.getLogger(__name__)


class TreasuryProfileService:
    """
    Service for managing company treasury profiles and continuous history validation.
    """
    
    # Business constants from settings with tolerance
    MINIMUM_HISTORY_MONTHS = settings.MIN_HISTORY_MONTHS
    MINIMUM_HISTORY_DAYS = 730
    RECOMMENDED_HISTORY_MONTHS = settings.ADVANCED_HISTORY_MONTHS
    OPTIMAL_HISTORY_MONTHS = settings.EXCELLENT_HISTORY_MONTHS
    HISTORY_TOLERANCE = settings.HISTORY_TOLERANCE
    
    REQUIRED_COLUMNS = ["date", "cash_inflow", "cash_outflow", "treasury_balance", "scheduled_receipts", "overdue_receipts", "scheduled_payments", "overdue_payments"]
    RECOMMENDED_COLUMNS = []
    INTERNAL_COLUMNS = {
        "_id",
        "company_id",
        "upload_id",
        "created_at",
        "updated_at",
        "uploaded_at",
    }
    
    def __init__(self):
        self.requirements = TreasuryRequirementsModel()
        self.daily_validator = DailyDataValidator()

    def _company_object_id(self, company_id: Any) -> ObjectId:
        """Normalize company IDs before every profile query."""
        try:
            return ObjectId(company_id)
        except Exception as exc:
            raise ValueError(
                f"Invalid company_id for treasury profile lookup: "
                f"{company_id!r} ({type(company_id).__name__})"
            ) from exc

    def _profile_query(self, company_id: Any) -> Dict[str, ObjectId]:
        return {"company_id": self._company_object_id(company_id)}

    def _profile_from_doc(self, profile_doc: Dict[str, Any]) -> TreasuryProfileModel:
        profile_doc = dict(profile_doc)
        profile_doc["_id"] = str(profile_doc["_id"])
        profile_doc["company_id"] = str(profile_doc["company_id"])
        
        # Calculate missing fields for existing profiles with tolerance
        if "forecasting_enabled" not in profile_doc or profile_doc["forecasting_enabled"] is None:
            profile_doc["forecasting_enabled"] = profile_doc.get("historical_months", 0) >= (self.MINIMUM_HISTORY_MONTHS - self.HISTORY_TOLERANCE)
        
        if "data_maturity" not in profile_doc or profile_doc["data_maturity"] is None:
            months = profile_doc.get("historical_months", 0)
            if months < (self.MINIMUM_HISTORY_MONTHS - self.HISTORY_TOLERANCE):
                profile_doc["data_maturity"] = "low"
            elif months < (self.RECOMMENDED_HISTORY_MONTHS - self.HISTORY_TOLERANCE):
                profile_doc["data_maturity"] = "medium"
            elif months < (self.OPTIMAL_HISTORY_MONTHS - self.HISTORY_TOLERANCE):
                profile_doc["data_maturity"] = "good"
            else:
                profile_doc["data_maturity"] = "optimal"
        
        return TreasuryProfileModel(**profile_doc)

    async def _analyze_stored_history(self, company_id: Any) -> Optional[Dict[str, Any]]:
        """
        Analyze the complete stored company history.

        Uploads can overlap. Profile depth must describe the canonical
        financial_records history, not the raw incoming file span.
        """
        query = self._profile_query(company_id)
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "earliest": {"$min": "$date"},
                    "latest": {"$max": "$date"},
                    "observed_days": {"$addToSet": "$date"},
                }
            },
        ]

        result = await database[c.FINANCIAL_RECORDS].aggregate(pipeline).to_list(1)
        if not result:
            return None

        earliest = result[0]["earliest"]
        latest = result[0]["latest"]
        days = (latest - earliest).days + 1

        return {
            "earliest": earliest,
            "latest": latest,
            "days": days,
            "months": round(days / 30.44, 2),
            "observed_days": len(result[0].get("observed_days", [])),
        }
    
    async def get_upload_requirements(self) -> TreasuryRequirementsModel:
        """
        Get treasury upload requirements for frontend display.
        
        Returns:
            Treasury requirements model with all validation rules
        """
        return self.requirements
    
    async def get_company_treasury_profile(self, company_id: str) -> Optional[TreasuryProfileModel]:
        """
        Get existing treasury profile for a company.
        
        Args:
            company_id: Company identifier (string)
            
        Returns:
            Treasury profile if exists, None otherwise
        """
        try:
            query = self._profile_query(company_id)
            logger.info(
                "company_treasury_profiles.find_one query=%s "
                "raw_company_id=%r raw_type=%s normalized_type=%s",
                query,
                company_id,
                type(company_id).__name__,
                type(query["company_id"]).__name__,
            )

            profile_doc = await database[c.COMPANY_TREASURY_PROFILES].find_one(query)
            
            if profile_doc:
                profile = self._profile_from_doc(profile_doc)
                # Update DB if fields were missing
                update_data = {}
                if "forecasting_enabled" not in profile_doc or profile_doc["forecasting_enabled"] is None:
                    update_data["forecasting_enabled"] = profile.forecasting_enabled
                if "data_maturity" not in profile_doc or profile_doc["data_maturity"] is None:
                    update_data["data_maturity"] = profile.data_maturity
                if update_data:
                    await database[c.COMPANY_TREASURY_PROFILES].update_one(query, {"$set": update_data})
                return profile
            
            logger.info(f"No treasury profile found for company {company_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get treasury profile for company {company_id}: {e}")
            raise
    
    async def create_treasury_profile(
        self, 
        company_id: str, 
        df: pd.DataFrame,
        upload_metadata: Dict[str, Any]
    ) -> TreasuryProfileModel:
        """
        Create initial treasury profile from first upload.
        
        Args:
            company_id: Company identifier (string)
            df: Processed DataFrame with treasury data
            upload_metadata: Upload processing metadata
            
        Returns:
            Created treasury profile
        """
        try:
            company_query = self._profile_query(company_id)
            logger.info(
                "Creating treasury profile for raw_company_id=%r raw_type=%s normalized_type=%s",
                company_id,
                type(company_id).__name__,
                type(company_query["company_id"]).__name__,
            )

            existing_profile = await self.get_company_treasury_profile(company_id)
            if existing_profile:
                logger.info(
                    "Treasury profile already exists for company %s; updating instead of inserting",
                    company_id,
                )
                return await self.update_treasury_profile(company_id, df, upload_metadata)
            
            # Analyze DataFrame structure
            detected_columns = df.columns.tolist()
            optional_columns = [
                col for col in detected_columns 
                if col not in self.REQUIRED_COLUMNS + self.RECOMMENDED_COLUMNS
                and col not in self.INTERNAL_COLUMNS
            ]
            
            # Calculate historical metrics
            date_range = await self._analyze_stored_history(company_id)
            if not date_range:
                date_range = self._analyze_date_range(df)
            history_level = self._calculate_history_level(date_range["days"])
            
            logger.info(
                f"Treasury profile metrics: days={date_range['days']}, "
                f"months={date_range['months']:.1f}, level={history_level.value}"
            )
            
            # Calculate forecasting_enabled and data_maturity
            forecasting_enabled = date_range["months"] >= 24
            months = date_range["months"]
            if months < 24:
                data_maturity = "low"
            elif months < 36:
                data_maturity = "medium"
            elif months < 48:
                data_maturity = "good"
            else:
                data_maturity = "optimal"
            
            # Create profile
            profile = TreasuryProfileModel(
                company_id=company_id,
                frequency="daily",
                required_columns=self.REQUIRED_COLUMNS,
                recommended_columns=self.RECOMMENDED_COLUMNS,
                optional_columns=optional_columns,
                historical_days=date_range["days"],
                historical_months=date_range["months"],
                history_level=history_level,
                forecasting_enabled=forecasting_enabled,
                data_maturity=data_maturity,
                first_upload_date=datetime.utcnow(),
                last_uploaded_date=datetime.utcnow(),
                earliest_data_date=date_range["earliest"],
                latest_data_date=date_range["latest"],
                total_uploads=1,
                structure_locked=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Save to database - CRITICAL: Store company_id as ObjectId
            profile_dict = profile.dict()
            profile_dict["company_id"] = company_query["company_id"]
            
            logger.info(
                "company_treasury_profiles.insert_one company_id=%s type=%s",
                profile_dict["company_id"],
                type(profile_dict["company_id"]).__name__,
            )
            
            await database[c.COMPANY_TREASURY_PROFILES].insert_one(profile_dict)
            
            logger.info(
                f"✅ Created treasury profile for company {company_id}: "
                f"{date_range['months']:.1f} months, {history_level.value} level"
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ Failed to create treasury profile for company {company_id}: {e}")
            raise
    
    async def update_treasury_profile(
        self,
        company_id: str,
        df: pd.DataFrame,
        upload_metadata: Dict[str, Any]
    ) -> TreasuryProfileModel:
        """
        Update existing treasury profile after successful upload.
        
        Args:
            company_id: Company identifier
            df: New DataFrame with treasury data
            upload_metadata: Upload processing metadata
            
        Returns:
            Updated treasury profile
        """
        try:
            company_query = self._profile_query(company_id)
            profile = await self.get_company_treasury_profile(company_id)
            if not profile:
                raise ValueError(f"No treasury profile found for company {company_id}")
            
            # Analyze new data range
            new_date_range = await self._analyze_stored_history(company_id)
            if not new_date_range:
                new_date_range = self._analyze_date_range(df)
            
            # Calculate updated historical metrics from canonical stored history.
            total_days = new_date_range["days"]
            total_months = new_date_range["months"]
            
            # Update optional columns if new ones detected
            new_columns = df.columns.tolist()
            new_optional = [
                col for col in new_columns 
                if col not in self.REQUIRED_COLUMNS + self.RECOMMENDED_COLUMNS
                and col not in self.INTERNAL_COLUMNS
                and col not in profile.optional_columns
            ]
            
            updated_optional = [
                col for col in profile.optional_columns
                if col not in self.INTERNAL_COLUMNS
            ] + new_optional
            
            # Calculate forecasting_enabled and data_maturity
            forecasting_enabled = total_months >= 24
            if total_months < 24:
                data_maturity = "low"
            elif total_months < 36:
                data_maturity = "medium"
            elif total_months < 48:
                data_maturity = "good"
            else:
                data_maturity = "optimal"
            
            # Update profile
            update_data = {
                "historical_days": total_days,
                "historical_months": total_months,
                "history_level": self._calculate_history_level(total_days),
                "forecasting_enabled": forecasting_enabled,
                "data_maturity": data_maturity,
                "last_uploaded_date": datetime.utcnow(),
                "earliest_data_date": new_date_range["earliest"],
                "latest_data_date": new_date_range["latest"],
                "total_uploads": profile.total_uploads + 1,
                "optional_columns": updated_optional,
                "updated_at": datetime.utcnow()
            }
            
            logger.info(
                "company_treasury_profiles.update_one query=%s "
                "raw_company_id=%r raw_type=%s normalized_type=%s",
                company_query,
                company_id,
                type(company_id).__name__,
                type(company_query["company_id"]).__name__,
            )
            await database[c.COMPANY_TREASURY_PROFILES].update_one(
                company_query,
                {"$set": update_data}
            )
            
            # Return updated profile
            updated_profile = await self.get_company_treasury_profile(company_id)
            
            logger.info(
                f"Updated treasury profile for company {company_id}: "
                f"{total_months:.1f} months total, {updated_profile.history_level.value} level"
            )
            
            return updated_profile
            
        except Exception as e:
            logger.error(f"Failed to update treasury profile for company {company_id}: {e}")
            raise
    
    async def validate_upload_structure(
        self, 
        company_id: str, 
        df: pd.DataFrame
    ) -> UploadValidationResult:
        """
        Validate upload structure and historical requirements.
        
        PHASE 3A: Enforces DAILY data requirement.
        Rejects monthly, quarterly, or yearly aggregated datasets.
        
        Args:
            company_id: Company identifier
            df: DataFrame to validate
            
        Returns:
            Validation result with detailed analysis
        """
        try:
            detected_columns = df.columns.tolist()
            missing_required = [
                col for col in self.REQUIRED_COLUMNS 
                if col not in detected_columns
            ]
            
            # Basic structure validation
            is_structurally_valid = len(missing_required) == 0
            
            # Date range analysis
            date_range = self._analyze_date_range(df) if is_structurally_valid else {
                "earliest": None, "latest": None, "days": 0, "months": 0.0
            }
            
            # Get existing profile first for all subsequent checks
            existing_profile = await self.get_company_treasury_profile(company_id)
            skip_historical_check = existing_profile is not None
            
            # History level assessment
            history_level = self._calculate_history_level(date_range["days"])
            
            structure_consistent = True
            structure_warnings = []
            
            if existing_profile:
                # Check structure consistency
                structure_result = self._validate_structure_consistency(
                    existing_profile, detected_columns
                )
                structure_consistent = structure_result["consistent"]
                structure_warnings = structure_result["warnings"]
                # In incremental mode, skip minimum history check on new file
                meets_minimum = True
            else:
                # Initial mode: check new file meets minimum history
                meets_minimum = date_range["months"] >= self.MINIMUM_HISTORY_MONTHS
            
            # PHASE 3A: Daily data enforcement - validate once only
            daily_validation = None
            is_daily_valid = False
            if is_structurally_valid:
                daily_validation = self.daily_validator.validate_daily_data(df, skip_historical_depth_check=skip_historical_check)
                is_daily_valid = daily_validation.is_valid
                
                logger.info(
                    f"Daily data validation for company {company_id}: "
                    f"frequency={daily_validation.frequency.value}, "
                    f"coverage={daily_validation.coverage_rate:.1%}, "
                    f"valid={is_daily_valid}"
                )
            
            # Build validation messages
            validation_messages = []
            business_messages = []
            
            if missing_required:
                business_messages.append(
                    f"Missing required columns: {', '.join(missing_required)}"
                )
            
            # PHASE 3A: Add daily data validation messages
            if daily_validation and not is_daily_valid:
                business_messages.extend(daily_validation.business_messages)
            
            if not meets_minimum and is_structurally_valid and is_daily_valid and not existing_profile:
                business_messages.append(
                    f"Current history: {date_range['months']:.1f} months. "
                    f"Minimum required: {self.MINIMUM_HISTORY_MONTHS} months"
                )
            
            # Overall validation: structure + daily data + (minimum history only if no existing profile)
            is_valid = is_structurally_valid and is_daily_valid and meets_minimum
            
            return UploadValidationResult(
                is_valid=is_valid,
                detected_columns=detected_columns,
                missing_required_columns=missing_required,
                earliest_date=date_range["earliest"],
                latest_date=date_range["latest"],
                detected_days=date_range["days"],
                detected_months=date_range["months"],
                validation_messages=validation_messages,
                business_messages=business_messages,
                structure_consistent=structure_consistent,
                structure_warnings=structure_warnings,
                chronology_valid=True,  # Will be validated separately for subsequent uploads
                chronology_messages=[],
                history_level=history_level,
                meets_minimum_requirement=meets_minimum,
                # PHASE 3A: Add daily validation details
                daily_frequency=daily_validation.frequency.value if daily_validation else "UNKNOWN",
                daily_coverage_rate=daily_validation.coverage_rate if daily_validation else 0.0,
                is_daily_data=is_daily_valid
            )
            
        except Exception as e:
            logger.error(f"Failed to validate upload structure for company {company_id}: {e}")
            return UploadValidationResult(
                is_valid=False,
                detected_columns=[],
                missing_required_columns=self.REQUIRED_COLUMNS,
                business_messages=[f"Validation error: {str(e)}"]
            )
    
    async def validate_chronological_continuity(
        self,
        company_id: str,
        df: pd.DataFrame
    ) -> ContinuityValidationResult:
        """
        Validate chronological continuity for subsequent uploads.
        
        Args:
            company_id: Company identifier
            df: New DataFrame to validate
            
        Returns:
            Continuity validation result
        """
        try:
            profile = await self.get_company_treasury_profile(company_id)
            if not profile or not profile.latest_data_date:
                # First upload - no continuity to check
                return ContinuityValidationResult(
                    is_continuous=True,
                    messages=["First upload - no continuity validation needed"]
                )
            
            # Analyze new data date range
            new_date_range = self._analyze_date_range(df)
            
            # Expected next date (day after last recorded date)
            expected_start = profile.latest_data_date + timedelta(days=1)
            received_start = new_date_range["earliest"]
            
            # Calculate gaps and overlaps
            if received_start > expected_start:
                # Gap detected
                gap_days = (received_start - expected_start).days
                return ContinuityValidationResult(
                    is_continuous=False,
                    expected_start_date=expected_start,
                    received_start_date=received_start,
                    gap_detected=True,
                    gap_days=gap_days,
                    messages=[
                        f"Historical continuity error. "
                        f"Expected period: {expected_start.strftime('%Y-%m')}. "
                        f"Received: {received_start.strftime('%Y-%m')}"
                    ]
                )
            
            elif received_start < expected_start:
                # Overlap or duplicate history. This is accepted here because
                # ContinuousHistoryService classifies duplicate/partial overlap
                # and imports only dates that are not already stored.
                overlap_days = (expected_start - received_start).days
                return ContinuityValidationResult(
                    is_continuous=True,
                    expected_start_date=expected_start,
                    received_start_date=received_start,
                    overlap_detected=True,
                    overlap_days=overlap_days,
                    messages=[
                        f"Data overlap detected and accepted. "
                        f"New data starts {overlap_days} days before expected date. "
                        f"Upload will import only new dates."
                    ]
                )
            
            else:
                # Perfect continuity
                return ContinuityValidationResult(
                    is_continuous=True,
                    expected_start_date=expected_start,
                    received_start_date=received_start,
                    messages=["Perfect chronological continuity"]
                )
                
        except Exception as e:
            logger.error(f"Failed to validate continuity for company {company_id}: {e}")
            return ContinuityValidationResult(
                is_continuous=False,
                messages=[f"Continuity validation error: {str(e)}"]
            )
    
    def _analyze_date_range(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze date range in DataFrame.
        
        Args:
            df: DataFrame with date column
            
        Returns:
            Dictionary with date range analysis
        """
        try:
            if 'date' not in df.columns:
                return {"earliest": None, "latest": None, "days": 0, "months": 0.0}
            
            # Ensure date column is datetime
            df_copy = df.copy()
            df_copy['date'] = pd.to_datetime(df_copy['date'])
            
            earliest = df_copy['date'].min()
            latest = df_copy['date'].max()
            days = (latest - earliest).days + 1  # Include both start and end dates
            months = round(days / 30.44, 2)
            
            return {
                "earliest": earliest.to_pydatetime(),
                "latest": latest.to_pydatetime(),
                "days": days,
                "months": months
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze date range: {e}")
            return {"earliest": None, "latest": None, "days": 0, "months": 0.0}
    
    def _calculate_history_level(self, days: int) -> HistoryLevel:
        """
        Calculate history maturity level based on days.
        
        Args:
            days: Number of historical days
            
        Returns:
            History level enum
        """
        months = days / 30.44
        
        if months < 24:
            return HistoryLevel.INSUFFICIENT
        elif months < 36:
            return HistoryLevel.READY
        elif months < 48:
            return HistoryLevel.ADVANCED
        else:
            return HistoryLevel.OPTIMAL
    
    def _validate_structure_consistency(
        self, 
        profile: TreasuryProfileModel, 
        new_columns: List[str]
    ) -> Dict[str, Any]:
        """
        Validate structure consistency against existing profile.
        
        Args:
            profile: Existing treasury profile
            new_columns: New upload columns
            
        Returns:
            Dictionary with consistency analysis
        """
        expected_columns = (
            profile.required_columns + 
            profile.recommended_columns + 
            profile.optional_columns
        )
        
        missing_columns = [col for col in expected_columns if col not in new_columns]
        new_optional_columns = [
            col for col in new_columns 
            if col not in expected_columns
        ]
        
        warnings = []
        
        if missing_columns:
            warnings.append(f"Missing previously used columns: {', '.join(missing_columns)}")
        
        if new_optional_columns:
            warnings.append(f"New optional columns detected: {', '.join(new_optional_columns)}")
        
        # Structure is consistent if no required/recommended columns are missing
        required_missing = [
            col for col in (profile.required_columns + profile.recommended_columns)
            if col not in new_columns
        ]
        
        return {
            "consistent": len(required_missing) == 0,
            "warnings": warnings,
            "missing_required": required_missing,
            "new_optional": new_optional_columns
        }
