"""Decision History & Action Tracking — Sprint 7."""

import logging
from datetime import date, datetime, timezone
from typing import Any

from app.utils.bson_utils import ObjectId

from app.db import collections as c
from app.db.mongodb import database
from app.services.business_intelligence_service import BusinessIntelligenceService

logger = logging.getLogger(__name__)

DECISION_SOURCES = frozenset({"executive_pdf", "dashboard", "manual"})
DECISION_PRIORITIES = frozenset({"low", "medium", "high", "critical"})
DECISION_STATUSES = frozenset({"pending", "in_progress", "completed", "cancelled"})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_for_mongo(obj: Any) -> Any:
    """
    Recursively convert datetime.date objects to datetime.datetime objects.
    MongoDB does not support datetime.date; only datetime.datetime is accepted.

    This function traverses the object and:
    - Converts date -> datetime (preserving timezone context)
    - Handles dicts and lists recursively
    """
    if isinstance(obj, date) and not isinstance(obj, datetime):
        # Convert date to datetime at midnight UTC
        return datetime.combine(obj, datetime.min.time()).replace(tzinfo=timezone.utc)
    elif isinstance(obj, dict):
        return {k: _serialize_for_mongo(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_for_mongo(item) for item in obj]
    else:
        return obj


def _serialize_doc(doc: dict | None) -> dict | None:
    if not doc:
        return None
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    out["company_id"] = str(out.get("company_id", ""))
    for field in ("decision_date", "created_at", "updated_at", "completed_at", "status_changed_at"):
        value = out.get(field)
        if isinstance(value, datetime):
            out[field] = value.isoformat()
        elif isinstance(value, date):
            out[field] = value.isoformat()
    if out.get("created_from_analysis_id") is not None:
        out["created_from_analysis_id"] = str(out["created_from_analysis_id"])
    return out


async def _capture_baseline_scores(company_id: str) -> dict[str, float | int]:
    """Snapshot current BI scores when a decision is recorded."""
    try:
        logger.info(f"Capturing baseline scores for company_id: {company_id}")
        bi = await BusinessIntelligenceService().generate(company_id)
        health = bi.get("financial_health_score") or {}
        resilience = bi.get("treasury_resilience_score") or {}
        runway = bi.get("cash_runway") or {}
        result = {
            "health": float(health.get("score") or 0),
            "resilience": float(resilience.get("score") or 0),
            "runway_days": int(runway.get("days") or 0),
        }
        logger.info(f"Baseline scores captured: {result}")
        return result
    except Exception as e:
        logger.exception(f"Failed to capture baseline scores for company {company_id}: {e}")
        return {"health": 0.0, "resilience": 0.0, "runway_days": 0}


async def _compute_impact(
    company_id: str,
    baseline: dict[str, float | int],
) -> dict[str, float | int]:
    """Compare current BI scores against baseline captured at decision creation."""
    try:
        logger.info(f"Computing impact for company_id: {company_id}, baseline: {baseline}")
        current = await _capture_baseline_scores(company_id)
        result = {
            "health_delta": round(current["health"] - baseline.get("health", 0), 1),
            "resilience_delta": round(current["resilience"] - baseline.get("resilience", 0), 1),
            "runway_delta": int(current["runway_days"] - baseline.get("runway_days", 0)),
        }
        logger.info(f"Computed impact: {result}")
        return result
    except Exception as e:
        logger.exception(f"Failed to compute impact: {e}")
        return {"health_delta": 0.0, "resilience_delta": 0.0, "runway_delta": 0}


def _impact_composite_score(impact: dict[str, Any] | None) -> float:
    if not impact:
        return 0.0
    health = float(impact.get("health_delta") or 0)
    resilience = float(impact.get("resilience_delta") or 0)
    runway = float(impact.get("runway_delta") or 0) / 5.0
    return round((health + resilience + runway) / 3.0, 2)


class DecisionService:
    async def create_decision(self, company_id: str, payload: dict) -> dict:
        now = _utcnow()
        decision_date = payload.get("decision_date") or now.date()
        if isinstance(decision_date, str):
            decision_date = date.fromisoformat(decision_date[:10])

        analysis_id = payload.get("created_from_analysis_id")
        baseline = await _capture_baseline_scores(company_id)

        doc = {
            "company_id": ObjectId(company_id),
            "decision_date": decision_date,
            "decision_title": payload["decision_title"].strip(),
            "decision_description": (payload.get("decision_description") or "").strip(),
            "source": payload.get("source") or "manual",
            "locale": payload.get("locale") or "fr",
            "priority": payload.get("priority") or "medium",
            "status": "pending",
            "expected_benefit": (payload.get("expected_benefit") or "").strip(),
            "created_from_analysis_id": ObjectId(analysis_id) if analysis_id else None,
            "baseline_scores": baseline,
            "impact": None,
            "created_at": now,
            "updated_at": now,
            "status_changed_at": now,
            "completed_at": None,
        }

        # Serialize date fields to datetime for MongoDB compatibility
        doc = _serialize_for_mongo(doc)

        result = await database[c.DECISION_HISTORY].insert_one(doc)
        created = await database[c.DECISION_HISTORY].find_one({"_id": result.inserted_id})
        return _serialize_doc(created)

    async def list_decisions(
        self,
        company_id: str,
        status: str | None = None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {"company_id": ObjectId(company_id)}
        if status:
            query["status"] = status

        cursor = database[c.DECISION_HISTORY].find(query).sort(
            [("decision_date", -1), ("created_at", -1)]
        )
        docs = [_serialize_doc(d) async for d in cursor]

        grouped = {s: [] for s in DECISION_STATUSES}
        for doc in docs:
            grouped.get(doc["status"], grouped["pending"]).append(doc)

        return {
            "decisions": docs,
            "grouped": grouped,
            "counts": {s: len(grouped[s]) for s in DECISION_STATUSES},
        }

    async def get_history_timeline(self, company_id: str, limit: int = 50) -> dict[str, Any]:
        cursor = database[c.DECISION_HISTORY].find(
            {"company_id": ObjectId(company_id)}
        ).sort([("decision_date", -1), ("created_at", -1)]).limit(limit)

        entries: list[dict[str, Any]] = []
        async for doc in cursor:
            serialized = _serialize_doc(doc)
            timeline_events = [
                {
                    "date": serialized["decision_date"],
                    "event_type": "decision",
                    "label": serialized["decision_title"],
                    "status": serialized["status"],
                    "priority": serialized["priority"],
                }
            ]
            if serialized.get("status") == "completed" and serialized.get("completed_at"):
                timeline_events.append(
                    {
                        "date": serialized["completed_at"][:10],
                        "event_type": "completed",
                        "label": "Décision réalisée",
                        "status": "completed",
                    }
                )
                if serialized.get("impact"):
                    impact = serialized["impact"]
                    timeline_events.append(
                        {
                            "date": serialized["completed_at"][:10],
                            "event_type": "impact",
                            "label": "Impact observé",
                            "impact": impact,
                        }
                    )
            entries.append(
                {
                    "decision_id": serialized["id"],
                    "decision_title": serialized["decision_title"],
                    "decision_date": serialized["decision_date"],
                    "status": serialized["status"],
                    "priority": serialized["priority"],
                    "expected_benefit": serialized.get("expected_benefit"),
                    "impact": serialized.get("impact"),
                    "completed_at": serialized.get("completed_at"),
                    "timeline": timeline_events,
                }
            )

        by_month: dict[str, list] = {}
        for entry in entries:
            month_key = entry["decision_date"][:7]
            by_month.setdefault(month_key, []).append(entry)

        return {
            "entries": entries,
            "by_month": by_month,
            "total": len(entries),
        }

    async def update_status(
        self,
        company_id: str,
        decision_id: str,
        new_status: str,
    ) -> dict:
        if new_status not in DECISION_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")

        doc = await database[c.DECISION_HISTORY].find_one(
            {"_id": ObjectId(decision_id), "company_id": ObjectId(company_id)}
        )
        if not doc:
            raise LookupError("Decision not found")

        now = _utcnow()
        update: dict[str, Any] = {
            "status": new_status,
            "updated_at": now,
            "status_changed_at": now,
        }

        if new_status == "completed":
            baseline = doc.get("baseline_scores") or {}
            impact = await _compute_impact(company_id, baseline)
            update["impact"] = impact
            update["completed_at"] = now
        elif new_status != "completed" and doc.get("status") == "completed":
            update["impact"] = None
            update["completed_at"] = None

        # Serialize date fields to datetime for MongoDB compatibility
        update = _serialize_for_mongo(update)

        await database[c.DECISION_HISTORY].update_one(
            {"_id": ObjectId(decision_id)},
            {"$set": update},
        )
        updated = await database[c.DECISION_HISTORY].find_one({"_id": ObjectId(decision_id)})
        return _serialize_doc(updated)

    async def get_impact_analytics(self, company_id: str) -> dict[str, Any]:
        cursor = database[c.DECISION_HISTORY].find(
            {"company_id": ObjectId(company_id)}
        )
        all_docs = [d async for d in cursor]

        total = len(all_docs)
        completed = [d for d in all_docs if d.get("status") == "completed"]
        completed_count = len(completed)
        execution_rate = round(completed_count / total * 100, 1) if total else 0.0

        impact_scores = [
            _impact_composite_score(d.get("impact"))
            for d in completed
            if d.get("impact")
        ]
        average_impact_score = (
            round(sum(impact_scores) / len(impact_scores), 2) if impact_scores else 0.0
        )

        aggregates = {"health_delta": 0.0, "resilience_delta": 0.0, "runway_delta": 0}
        for d in completed:
            impact = d.get("impact") or {}
            aggregates["health_delta"] += float(impact.get("health_delta") or 0)
            aggregates["resilience_delta"] += float(impact.get("resilience_delta") or 0)
            aggregates["runway_delta"] += int(impact.get("runway_delta") or 0)

        if completed_count:
            aggregates = {
                "health_delta": round(aggregates["health_delta"] / completed_count, 1),
                "resilience_delta": round(aggregates["resilience_delta"] / completed_count, 1),
                "runway_delta": round(aggregates["runway_delta"] / completed_count, 1),
            }

        return {
            "total_decisions": total,
            "completed_decisions": completed_count,
            "pending_decisions": sum(1 for d in all_docs if d.get("status") == "pending"),
            "in_progress_decisions": sum(1 for d in all_docs if d.get("status") == "in_progress"),
            "cancelled_decisions": sum(1 for d in all_docs if d.get("status") == "cancelled"),
            "execution_rate": execution_rate,
            "average_impact_score": average_impact_score,
            "average_impact_deltas": aggregates,
        }

    async def prepare_pdf_data(self, company_id: str, limit: int = 10) -> dict[str, Any]:
        """
        Prepare decision history payload for a future Executive PDF section.
        Does not modify the PDF generator — data-only export.
        """
        timeline = await self.get_history_timeline(company_id, limit=limit)
        analytics = await self.get_impact_analytics(company_id)

        completed_with_impact = [
            {
                "date": e["completed_at"][:10] if e.get("completed_at") else e["decision_date"],
                "title": e["decision_title"],
                "impact": e.get("impact"),
            }
            for e in timeline["entries"]
            if e["status"] == "completed" and e.get("impact")
        ]

        return {
            "decision_history_summary": {
                "total_decisions": analytics["total_decisions"],
                "completed_decisions": analytics["completed_decisions"],
                "execution_rate": analytics["execution_rate"],
                "average_impact_score": analytics["average_impact_score"],
            },
            "recent_decisions": timeline["entries"][:limit],
            "completed_with_impact": completed_with_impact,
            "by_month": timeline["by_month"],
        }

    async def recompute_impact(self, company_id: str) -> dict[str, Any]:
        """Recompute impact for all completed decisions with baseline scores."""
        logger.info(f"Recomputing impact for company_id: {company_id}")
        cursor = database[c.DECISION_HISTORY].find(
            {
                "company_id": ObjectId(company_id),
                "status": "completed",
                "baseline_scores": {"$exists": True},
            }
        )
        updated_count = 0

        async for decision in cursor:
            try:
                baseline = decision.get("baseline_scores") or {}
                impact = await _compute_impact(company_id, baseline)
                await database[c.DECISION_HISTORY].update_one(
                    {"_id": decision["_id"]},
                    {"$set": {"impact": impact, "updated_at": _utcnow()}},
                )
                updated_count += 1
                logger.info(f"Updated decision {decision['_id']} with impact: {impact}")
            except Exception as e:
                logger.exception(f"Failed to update decision {decision.get('_id')}: {e}")

        return {"updated": updated_count}
