"""
Audit Service — Logging and tracking for compliance and debugging.

Responsibilities:
- Log all user actions (uploads, forecasts, etc.)
- Track subscription changes
- Record admin actions
- Provide audit trail for compliance
- Track system errors and failures
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.db import collections as c
from app.db.mongodb import database

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────────────────────
# Upload Audit Logging
# ──────────────────────────────────────────────────────────────────────────────

async def log_upload(
    action: str,
    upload_id: str,
    user_id: str,
    company_id: Optional[str] = None,
    filename: Optional[str] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    details: Optional[dict] = None,
    request: Optional[dict] = None,
) -> None:
    """
    Log an upload-related action.

    Args:
        action: Action type (e.g., "upload_started", "upload_completed", "upload_failed", "duplicate_detected")
        upload_id: ID of the upload document
        user_id: ID of the user performing the action
        company_id: Optional company ID
        filename: Optional original filename
        status: Optional status (success, failed, warning)
        error_message: Optional error message if failed
        details: Optional additional details dict
        request: Optional request object (ignored, for compatibility)
    """
    try:
        audit_doc = {
            "timestamp": _utcnow(),
            "event_type": "upload",
            "action": action,
            "user_id": user_id,
            "upload_id": upload_id,
            "company_id": company_id,
            "filename": filename,
            "status": status,
            "error_message": error_message,
            "details": details or {},
        }

        await database[c.AUDIT_LOGS].insert_one(audit_doc)
        logger.debug(f"Audit log: {action} for upload {upload_id}")
    except Exception as e:
        logger.error(f"Failed to log upload action: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Subscription Audit Logging
# ──────────────────────────────────────────────────────────────────────────────

async def log_subscription_upgrade(
    user_id: str,
    from_plan: str,
    to_plan: str,
    company_id: Optional[str] = None,
    payment_amount: Optional[float] = None,
    status: str = "success",
) -> None:
    """
    Log a subscription upgrade event.

    Args:
        user_id: ID of the user upgrading
        from_plan: Previous plan code
        to_plan: New plan code
        company_id: Optional company ID
        payment_amount: Optional payment amount
        status: Status of the upgrade (success, failed, etc.)
    """
    try:
        audit_doc = {
            "timestamp": _utcnow(),
            "event_type": "subscription",
            "action": "upgrade",
            "user_id": user_id,
            "company_id": company_id,
            "from_plan": from_plan,
            "to_plan": to_plan,
            "payment_amount": payment_amount,
            "status": status,
        }

        await database[c.AUDIT_LOGS].insert_one(audit_doc)
        logger.info(f"Subscription upgrade: {user_id} {from_plan} → {to_plan}")
    except Exception as e:
        logger.error(f"Failed to log subscription upgrade: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# General Action Logging
# ──────────────────────────────────────────────────────────────────────────────

async def log_action(
    user_id: str,
    action: str,
    company_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """
    Log a general user action.

    Args:
        user_id: ID of the user performing the action
        action: Action type
        company_id: Optional company ID
        details: Optional additional details dict
    """
    try:
        audit_doc = {
            "timestamp": _utcnow(),
            "event_type": "action",
            "action": action,
            "user_id": user_id,
            "company_id": company_id,
            "details": details or {},
        }

        await database[c.AUDIT_LOGS].insert_one(audit_doc)
        logger.debug(f"Audit log: {action} by user {user_id}")
    except Exception as e:
        logger.error(f"Failed to log action: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Admin Action Logging
# ──────────────────────────────────────────────────────────────────────────────

async def log_admin_action(
    admin_user_id: str,
    action: str,
    details: Optional[dict] = None,
) -> None:
    """
    Log an admin action.

    Args:
        admin_user_id: ID of the admin user
        action: Action type (e.g., "admin_audit_access", "admin_failures_access")
        details: Optional additional details dict
    """
    try:
        audit_doc = {
            "timestamp": _utcnow(),
            "event_type": "admin",
            "action": action,
            "admin_user_id": admin_user_id,
            "details": details or {},
        }

        await database[c.AUDIT_LOGS].insert_one(audit_doc)
        logger.debug(f"Admin audit log: {action} by admin {admin_user_id}")
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Audit Statistics and Retrieval
# ──────────────────────────────────────────────────────────────────────────────

async def get_recent_failures(
    hours: int = 24,
    limit: int = 100,
    company_id: Optional[str] = None,
) -> list[dict]:
    """
    Get recent upload failures.

    Args:
        hours: Look back this many hours
        limit: Maximum number of records to return
        company_id: Optional filter by company

    Returns:
        List of failure audit records
    """
    try:
        cutoff_time = datetime.now(timezone.utc)
        cutoff_time = cutoff_time.replace(hour=cutoff_time.hour - hours)

        query = {
            "event_type": "upload",
            "action": "upload_failed",
            "timestamp": {"$gte": cutoff_time},
        }

        if company_id:
            query["company_id"] = company_id

        failures = await database[c.AUDIT_LOGS].find(query).limit(limit).to_list(None)
        return failures or []
    except Exception as e:
        logger.error(f"Failed to get recent failures: {e}")
        return []


async def get_audit_stats(hours: int = 1) -> dict:
    """
    Get audit statistics for the last N hours.

    Args:
        hours: Look back this many hours

    Returns:
        Dict with stats like error_rate, total_events, etc.
    """
    try:
        cutoff_time = datetime.now(timezone.utc)
        cutoff_time = cutoff_time.replace(hour=cutoff_time.hour - hours)

        # Count total events
        total_events = await database[c.AUDIT_LOGS].count_documents(
            {"timestamp": {"$gte": cutoff_time}}
        )

        # Count failures
        failures = await database[c.AUDIT_LOGS].count_documents(
            {
                "event_type": "upload",
                "action": "upload_failed",
                "timestamp": {"$gte": cutoff_time},
            }
        )

        error_rate = (failures / total_events * 100) if total_events > 0 else 0

        return {
            "total_events": total_events,
            "failures": failures,
            "error_rate": round(error_rate, 2),
            "period_hours": hours,
        }
    except Exception as e:
        logger.error(f"Failed to get audit stats: {e}")
        return {
            "total_events": 0,
            "failures": 0,
            "error_rate": 0,
            "period_hours": hours,
        }
