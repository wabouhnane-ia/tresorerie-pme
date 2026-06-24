"""Notification Service — CRUD and retrieval for alerts and notifications."""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.utils.bson_utils import ObjectId
from app.db import collections as c
from app.db.mongodb import database
from app.services.decision_service import _serialize_for_mongo


class NotificationService:
    """Manages notification creation, retrieval, and lifecycle."""

    async def create_notification(
        self,
        company_id: str,
        notification_type: str,
        severity: str,
        title: str,
        message: str,
        source: str,
        metadata: dict | None = None,
        expires_in_days: int | None = None,
    ) -> dict:
        """Create a new notification."""
        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_in_days:
            expires_at = now + timedelta(days=expires_in_days)

        doc = {
            "company_id": ObjectId(company_id),
            "type": notification_type,
            "severity": severity,
            "title": title,
            "message": message,
            "source": source,
            "is_read": False,
            "created_at": now,
            "expires_at": expires_at,
            "metadata": metadata or {},
        }

        # Serialize for MongoDB compatibility (handles date fields if any)
        doc = _serialize_for_mongo(doc)

        result = await database[c.NOTIFICATIONS].insert_one(doc)
        created = await database[c.NOTIFICATIONS].find_one({"_id": result.inserted_id})
        return self._serialize_notification(created)

    async def create_bulk_notifications(
        self,
        company_id: str,
        notifications: list[dict],
    ) -> list[dict]:
        """Insert multiple notifications at once (from alert engine)."""
        if not notifications:
            return []

        docs = []
        for notif in notifications:
            doc = {
                "company_id": ObjectId(company_id),
                "type": notif.get("type", "warning"),
                "severity": notif.get("severity", "medium"),
                "title": notif["title"],
                "message": notif["message"],
                "source": notif.get("source", "business_intelligence"),
                "is_read": False,
                "created_at": notif.get("created_at", datetime.now(timezone.utc)),
                "expires_at": notif.get("expires_at"),
                "metadata": notif.get("metadata", {}),
            }
            doc = _serialize_for_mongo(doc)
            docs.append(doc)

        if not docs:
            return []

        result = await database[c.NOTIFICATIONS].insert_many(docs)
        created = await database[c.NOTIFICATIONS].find(
            {"_id": {"$in": result.inserted_ids}}
        ).to_list(None)
        return [self._serialize_notification(doc) for doc in created]

    async def list_notifications(
        self,
        company_id: str,
        unread_only: bool = False,
        limit: int = 50,
        skip: int = 0,
        locale: str | None = None,
    ) -> dict[str, Any]:
        """List notifications for a company."""
        query: dict[str, Any] = {"company_id": ObjectId(company_id)}
        if unread_only:
            query["is_read"] = False

        # Also exclude expired notifications
        query["$or"] = [
            {"expires_at": None},
            {"expires_at": {"$gt": datetime.now(timezone.utc)}},
        ]

        cursor = database[c.NOTIFICATIONS].find(query).sort(
            [("created_at", -1)]
        ).skip(skip).limit(limit)
        
        notifications = [self._serialize_notification(doc, locale=locale) async for doc in cursor]

        # Get total count
        total = await database[c.NOTIFICATIONS].count_documents(query)

        # Get unread count
        unread_query = {**query, "is_read": False}
        unread_count = await database[c.NOTIFICATIONS].count_documents(unread_query)

        return {
            "notifications": notifications,
            "total": total,
            "unread": unread_count,
            "has_more": (skip + limit) < total,
        }

    async def get_unread_notifications(
        self,
        company_id: str,
        locale: str | None = None,
    ) -> dict[str, Any]:
        """Get all unread notifications (for bell icon)."""
        query = {
            "company_id": ObjectId(company_id),
            "is_read": False,
            "$or": [
                {"expires_at": None},
                {"expires_at": {"$gt": datetime.now(timezone.utc)}},
            ],
        }

        cursor = database[c.NOTIFICATIONS].find(query).sort([("created_at", -1)]).limit(100)
        notifications = [self._serialize_notification(doc, locale=locale) async for doc in cursor]

        # Count by severity
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for notif in notifications:
            severity = notif.get("severity", "low")
            if severity in by_severity:
                by_severity[severity] += 1

        return {
            "notifications": notifications,
            "total": len(notifications),
            "by_severity": by_severity,
            "has_critical": by_severity["critical"] > 0,
        }

    async def mark_as_read(self, company_id: str, notification_id: str) -> dict:
        """Mark a single notification as read."""
        result = await database[c.NOTIFICATIONS].find_one_and_update(
            {
                "_id": ObjectId(notification_id),
                "company_id": ObjectId(company_id),
            },
            {"$set": {"is_read": True}},
            return_document=True,
        )
        if not result:
            raise LookupError("Notification not found")
        return self._serialize_notification(result)

    async def mark_all_as_read(self, company_id: str) -> dict:
        """Mark all unread notifications as read."""
        await database[c.NOTIFICATIONS].update_many(
            {
                "company_id": ObjectId(company_id),
                "is_read": False,
            },
            {"$set": {"is_read": True}},
        )

        # Return updated count
        all_read = await database[c.NOTIFICATIONS].count_documents(
            {
                "company_id": ObjectId(company_id),
                "is_read": True,
            }
        )

        return {
            "success": True,
            "total_read": all_read,
        }

    async def delete_notification(self, company_id: str, notification_id: str) -> dict:
        """Delete a notification."""
        result = await database[c.NOTIFICATIONS].delete_one(
            {
                "_id": ObjectId(notification_id),
                "company_id": ObjectId(company_id),
            }
        )
        if result.deleted_count == 0:
            raise LookupError("Notification not found")
        return {"deleted": True}

    async def delete_old_notifications(self, company_id: str, older_than_days: int = 30) -> dict:
        """Delete old read notifications (cleanup)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        result = await database[c.NOTIFICATIONS].delete_many(
            {
                "company_id": ObjectId(company_id),
                "is_read": True,
                "created_at": {"$lt": cutoff},
            }
        )
        return {"deleted_count": result.deleted_count}

    async def get_statistics(self, company_id: str) -> dict[str, Any]:
        """Get notification statistics."""
        query = {"company_id": ObjectId(company_id)}

        total = await database[c.NOTIFICATIONS].count_documents(query)
        unread = await database[c.NOTIFICATIONS].count_documents({**query, "is_read": False})
        critical = await database[c.NOTIFICATIONS].count_documents(
            {**query, "severity": "critical"}
        )

        # Count by type
        by_type_docs = await database[c.NOTIFICATIONS].aggregate(
            [
                {"$match": query},
                {"$group": {"_id": "$type", "count": {"$sum": 1}}},
            ]
        ).to_list(None)
        by_type = {doc["_id"]: doc["count"] for doc in by_type_docs}

        # Count by severity
        by_severity_docs = await database[c.NOTIFICATIONS].aggregate(
            [
                {"$match": query},
                {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
            ]
        ).to_list(None)
        by_severity = {doc["_id"]: doc["count"] for doc in by_severity_docs}

        return {
            "total_notifications": total,
            "unread_notifications": unread,
            "critical_notifications": critical,
            "by_type": by_type,
            "by_severity": by_severity,
        }

    @staticmethod
    def _serialize_notification(doc: dict | None, locale: str | None = None) -> dict | None:
        """Convert MongoDB document to API response."""
        if not doc:
            return None

        return {
            "id": str(doc.get("_id", "")),
            "type": doc.get("type"),
            "severity": doc.get("severity"),
            "title": doc.get("title"),
            "message": doc.get("message"),
            "source": doc.get("source"),
            "is_read": doc.get("is_read", False),
            "created_at": doc.get("created_at").isoformat()
            if doc.get("created_at")
            else None,
            "expires_at": doc.get("expires_at").isoformat()
            if doc.get("expires_at")
            else None,
            "metadata": doc.get("metadata", {}),
            "language": locale or (doc.get("metadata") or {}).get("locale"),
        }
