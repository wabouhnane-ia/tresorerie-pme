"""
AI Insights Service
Manage storage and retrieval of canonical executive AI analysis.
"""

from datetime import datetime, timezone
from typing import Optional

from app.utils.bson_utils import ObjectId

from app.db import collections as c
from app.db.mongodb import database


async def store_ai_insights(
    company_id: str,
    executive_analysis: dict,
    forecast_metrics: dict,
    recommendations: list[dict],
    scenario: str | None = None,
) -> str:
    """
    Store canonical AI executive analysis for future retrieval.
    """
    
    if not executive_analysis:
        raise ValueError("No executive_analysis provided")
    
    insight_doc = {
        "company_id": ObjectId(company_id),
        "scenario": scenario,
        "created_at": datetime.now(timezone.utc),
        "executive_analysis": executive_analysis,
        "forecast_context": forecast_metrics,
        "recommendations_count": len(recommendations),
        "critical_recommendations": len([r for r in recommendations if r.get("severity") == "critical"]),
        "is_active": True,
    }
    
    result = await database[c.AI_INSIGHTS].insert_one(insight_doc)
    return str(result.inserted_id)


async def get_latest_ai_insights(
    company_id: str,
    scenario: str | None = None,
) -> Optional[dict]:
    """Get most recent AI insights for the company."""
    
    query = {
        "company_id": ObjectId(company_id),
        "is_active": True,
    }
    
    if scenario:
        query["scenario"] = scenario
        
    doc = await database[c.AI_INSIGHTS].find_one(
        query,
        sort=[("created_at", -1)]
    )
    
    if not doc:
        return None
    
    return {
        "id": str(doc["_id"]),
        "executive_analysis": doc.get("executive_analysis", {}),
        "forecast_context": doc.get("forecast_context", {}),
        "recommendations_count": doc.get("recommendations_count", 0),
        "critical_recommendations": doc.get("critical_recommendations", 0),
        "generated_at": doc.get("created_at", "").isoformat() if doc.get("created_at") else "",
        "scenario": doc.get("scenario"),
    }


async def get_ai_insights_history(
    company_id: str,
    limit: int = 10,
) -> list[dict]:
    """Get historical AI insights."""
    
    cursor = database[c.AI_INSIGHTS].find(
        {"company_id": ObjectId(company_id)},
        sort=[("created_at", -1)],
    ).limit(limit)
    
    results = []
    async for doc in cursor:
        results.append({
            "id": str(doc["_id"]),
            "scenario": doc.get("scenario"),
            "generated_at": doc.get("created_at", "").isoformat() if doc.get("created_at") else "",
            "summary": doc.get("executive_analysis", {}).get("executive_summary", "")[:100],
        })
    
    return results
