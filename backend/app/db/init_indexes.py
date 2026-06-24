"""Create MongoDB indexes for multi-tenant SaaS collections."""

import logging
from app.db import collections as c
from app.db.mongodb import database

logger = logging.getLogger(__name__)


async def init_indexes() -> None:
    """Create all necessary indexes for the application."""
    
    # ──────────────────────────────────────────────────────────────────────────
    # Core Collections
    # ──────────────────────────────────────────────────────────────────────────
    
    try:
        await database[c.USERS].create_index("email", unique=True)
    except Exception as e:
        logger.warning(f"Index creation failed for users.email: {e}")

    try:
        await database[c.MEMBERSHIPS].create_index(
            [("user_id", 1), ("company_id", 1)],
            unique=True,
        )
    except Exception as e:
        logger.warning(f"Index creation failed for memberships (user_id, company_id): {e}")

    try:
        await database[c.MEMBERSHIPS].create_index("company_id")
    except Exception as e:
        logger.warning(f"Index creation failed for memberships.company_id: {e}")

    try:
        await database[c.COMPANIES].create_index([("status", 1), ("created_at", -1)])
    except Exception as e:
        logger.warning(f"Index creation failed for companies: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # SaaS Billing Collections
    # ──────────────────────────────────────────────────────────────────────────
    
    try:
        await database[c.SUBSCRIPTION_PLANS].create_index("code", unique=True)
    except Exception as e:
        logger.warning(f"Index creation failed for subscription_plans.code: {e}")

    try:
        await database[c.SUBSCRIPTIONS].create_index("company_id", unique=True)
    except Exception as e:
        logger.warning(f"Index creation failed for subscriptions.company_id: {e}")

    try:
        await database[c.SUBSCRIPTIONS].create_index(
            [("status", 1), ("updated_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for subscriptions (status, updated_at): {e}")

    try:
        await database[c.PAYMENTS].create_index(
            [("company_id", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for payments: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Data Management Collections
    # ──────────────────────────────────────────────────────────────────────────
    
    try:
        await database[c.UPLOADS].create_index(
            [("company_id", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for uploads (company_id, created_at): {e}")

    try:
        await database[c.UPLOADS].create_index(
            [("company_id", 1), ("status", 1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for uploads (company_id, status): {e}")

    try:
        await database[c.UPLOADS].create_index("upload_id")
    except Exception as e:
        logger.warning(f"Index creation failed for uploads.upload_id: {e}")

    try:
        await database[c.FINANCIAL_RECORDS].create_index(
            [("company_id", 1), ("date", 1)],
            unique=True,
        )
    except Exception as e:
        logger.warning(f"Index creation failed for financial_records (company_id, date): {e}")

    try:
        await database[c.FINANCIAL_RECORDS].create_index("upload_id")
    except Exception as e:
        logger.warning(f"Index creation failed for financial_records.upload_id: {e}")

    try:
        await database[c.DATA_QUALITY_REPORTS].create_index(
            [("company_id", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for data_quality_reports: {e}")

    try:
        await database[c.DATA_QUALITY_REPORTS].create_index("upload_id")
    except Exception as e:
        logger.warning(f"Index creation failed for data_quality_reports.upload_id: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 3: Continuous Treasury History Platform
    # ──────────────────────────────────────────────────────────────────────────
    
    try:
        await database[c.COMPANY_TREASURY_PROFILES].create_index(
            "company_id",
            unique=True,
        )
    except Exception as e:
        logger.warning(f"Index creation failed for company_treasury_profiles.company_id: {e}")

    try:
        await database[c.COMPANY_TREASURY_PROFILES].create_index("updated_at")
    except Exception as e:
        logger.warning(f"Index creation failed for company_treasury_profiles.updated_at: {e}")

    try:
        await database[c.COMPANY_TREASURY_PROFILES].create_index("history_level")
    except Exception as e:
        logger.warning(f"Index creation failed for company_treasury_profiles.history_level: {e}")

    try:
        await database[c.COMPANY_TREASURY_PROFILES].create_index("latest_data_date")
    except Exception as e:
        logger.warning(f"Index creation failed for company_treasury_profiles.latest_data_date: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Forecasting Collections
    # ──────────────────────────────────────────────────────────────────────────
    
    try:
        await database[c.FORECAST_RUNS].create_index(
            [("company_id", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for forecast_runs (company_id, created_at): {e}")

    try:
        await database[c.FORECAST_RUNS].create_index(
            [("company_id", 1), ("status", 1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for forecast_runs (company_id, status): {e}")

    try:
        await database[c.FORECASTS].create_index(
            [("forecast_run_id", 1), ("ds", 1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for forecasts (forecast_run_id, ds): {e}")

    try:
        await database[c.FORECASTS].create_index("company_id")
    except Exception as e:
        logger.warning(f"Index creation failed for forecasts.company_id: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Analytics Collections
    # ──────────────────────────────────────────────────────────────────────────
    
    try:
        await database[c.RISK_ASSESSMENTS].create_index(
            [("company_id", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for risk_assessments: {e}")

    try:
        await database[c.RECOMMENDATIONS].create_index(
            [("company_id", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for recommendations: {e}")

    try:
        await database[c.AI_INSIGHTS].create_index(
            [("company_id", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for ai_insights: {e}")

    try:
        await database[c.DECISION_HISTORY].create_index(
            [("company_id", 1), ("decision_date", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for decision_history (company_id, decision_date): {e}")

    try:
        await database[c.DECISION_HISTORY].create_index(
            [("company_id", 1), ("status", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for decision_history (company_id, status): {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Audit Collections
    # ──────────────────────────────────────────────────────────────────────────
    
    try:
        await database[c.AUDIT_LOGS].create_index(
            [("company_id", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for audit_logs (company_id, created_at): {e}")

    try:
        await database[c.AUDIT_LOGS].create_index(
            "created_at",
            expireAfterSeconds=60 * 60 * 24 * 90,  # 90 days TTL
        )
    except Exception as e:
        logger.warning(f"Index creation failed for audit_logs TTL: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Sprint 8: Notification Center
    # ──────────────────────────────────────────────────────────────────────────
    
    try:
        await database[c.NOTIFICATIONS].create_index(
            [("company_id", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for notifications (company_id, created_at): {e}")

    try:
        await database[c.NOTIFICATIONS].create_index(
            [("company_id", 1), ("is_read", 1), ("created_at", -1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for notifications (company_id, is_read, created_at): {e}")

    try:
        await database[c.NOTIFICATIONS].create_index(
            [("company_id", 1), ("severity", 1)]
        )
    except Exception as e:
        logger.warning(f"Index creation failed for notifications (company_id, severity): {e}")

    try:
        await database[c.NOTIFICATIONS].create_index(
            "expires_at",
            expireAfterSeconds=0,  # Delete documents when expires_at is reached
        )
    except Exception as e:
        logger.warning(f"Index creation failed for notifications TTL: {e}")

    logger.info("✅ All indexes created successfully")
