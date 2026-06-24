"""Admin API — Super admin observability and audit endpoints.

Provides comprehensive audit logging access and platform observability
for super admin users only.

Features:
- Audit log access with filtering and pagination
- Platform observability metrics
- Recent failures monitoring
- Admin action tracking
- Company activity monitoring
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.bson_utils import ObjectId

from app.auth.dependencies import get_current_user
from app.db import collections as c
from app.db.mongodb import database
from app.services import audit_service
from app.services.subscription_service import get_admin_subscription_analytics, is_super_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


def require_super_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure only super admin can access admin endpoints."""
    if not is_super_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Super admin access required"
        )
    return current_user


@router.get("/audit-logs")
async def get_audit_logs(
    admin_user: dict = Depends(require_super_admin),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    status: Optional[str] = Query(None, description="Filter by status (success/failed/warning)"),
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
):
    """
    Get audit logs with filtering and pagination.
    
    Only accessible to super admin users.
    Supports filtering by action, status, company, user, and resource type.
    """
    try:
        # Build query filter
        query = {}
        
        if action:
            query["action"] = action
        if status:
            query["status"] = status
        if company_id:
            query["company_id"] = ObjectId(company_id)
        if user_id:
            query["user_id"] = ObjectId(user_id)
        if resource_type:
            query["resource_type"] = resource_type
        
        # Calculate skip for pagination
        skip = (page - 1) * limit
        
        # Get audit logs from database
        from app.db import collections as c
        from app.db.mongodb import database
        
        cursor = (
            database[c.AUDIT_LOGS]
            .find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        
        logs = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if doc.get("user_id"):
                doc["user_id"] = str(doc["user_id"])
            if doc.get("company_id"):
                doc["company_id"] = str(doc["company_id"])
            if doc.get("resource_id"):
                doc["resource_id"] = str(doc["resource_id"])
            logs.append(doc)
        
        # Get total count for pagination
        total_count = await database[c.AUDIT_LOGS].count_documents(query)
        total_pages = (total_count + limit - 1) // limit
        
        # Log admin access
        await audit_service.log_admin_action(
            action="admin_audit_access",
            admin_user_id=str(admin_user["_id"]),
            target_resource_type="audit_logs",
            details={
                "filters": query,
                "page": page,
                "limit": limit,
                "results_count": len(logs)
            }
        )
        
        return {
            "logs": logs,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "filters_applied": query
        }
        
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit logs")


@router.get("/recent-failures")
async def get_recent_failures(
    admin_user: dict = Depends(require_super_admin),
    limit: int = Query(50, ge=1, le=200, description="Number of failures to return"),
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
):
    """
    Get recent failed actions for monitoring.
    
    Only accessible to super admin users.
    """
    try:
        failures = await audit_service.get_recent_failures(
            limit=limit,
            company_id=company_id
        )
        
        # Log admin access
        await audit_service.log_admin_action(
            action="admin_failures_access",
            admin_user_id=str(admin_user["_id"]),
            target_resource_type="audit_logs",
            details={
                "limit": limit,
                "company_id": company_id,
                "failures_count": len(failures)
            }
        )
        
        return {
            "failures": failures,
            "count": len(failures),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent failures: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent failures")


@router.get("/health")
async def admin_health_check(
    admin_user: dict = Depends(require_super_admin),
):
    """
    Admin health check endpoint with system status.
    
    Only accessible to super admin users.
    """
    try:
        # Get basic system health metrics
        from app.db.mongodb import database
        
        # Test database connectivity
        db_status = "healthy"
        try:
            await database.command("ping")
        except Exception:
            db_status = "unhealthy"
        
        # Get recent error rate
        recent_stats = await audit_service.get_audit_stats(hours=1)
        error_rate = recent_stats.get("error_rate", 0)
        
        health_status = {
            "status": "healthy" if db_status == "healthy" and error_rate < 0.1 else "degraded",
            "database": db_status,
            "error_rate_1h": error_rate,
            "total_events_1h": recent_stats.get("total_events", 0),
            "timestamp": audit_service._utcnow().isoformat()
        }
        
        # Log admin access
        await audit_service.log_admin_action(
            action="admin_health_check",
            admin_user_id=str(admin_user["_id"]),
            target_resource_type="system",
            details=health_status
        )
        
        return health_status
        
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve health status")


@router.get("/subscription-analytics")
async def subscription_analytics(admin_user: dict = Depends(require_super_admin)):
    """SaaS metrics: trials, active, expired, MRR, ARR."""
    try:
        metrics = await get_admin_subscription_analytics()
        await audit_service.log_admin_action(
            action="admin_subscription_analytics",
            admin_user_id=str(admin_user["_id"]),
            target_resource_type="subscriptions",
            details=metrics,
        )
        return metrics
    except Exception as e:
        logger.error(f"Failed to get subscription analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


@router.get("/users-subscriptions")
async def list_users_subscriptions(
    admin_user: dict = Depends(require_super_admin),
    limit: int = Query(50, ge=1, le=200),
):
    """List users with subscription and usage (super admin only)."""
    cursor = database[c.USERS].find().sort("created_at", -1).limit(limit)
    items = []
    async for user in cursor:
        sub = user.get("subscription") or {}
        usage = user.get("usage") or {}
        items.append({
            "user_id": str(user["_id"]),
            "email": user.get("email"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "role": user.get("role", "owner"),
            "plan_code": sub.get("plan_code", "free_trial"),
            "total_uploads": usage.get("total_uploads", 0),
            "total_forecast_runs": usage.get("total_forecast_runs", 0),
            "created_at": user.get("created_at"),
        })
    return {"users": items, "count": len(items)}