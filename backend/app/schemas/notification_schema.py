"""Notification schemas for Alert Center."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


NotificationType = Literal[
    "risk",
    "warning",
    "opportunity",
    "decision",
    "success",
]

NotificationSeverity = Literal[
    "low",
    "medium",
    "high",
    "critical",
]

NotificationSource = Literal[
    "business_intelligence",
    "decision_center",
    "forecast",
    "risk_engine",
]


class NotificationSchema(BaseModel):
    """Notification document model."""

    type: NotificationType
    severity: NotificationSeverity
    title: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10, max_length=2000)
    source: NotificationSource
    is_read: bool = False
    created_at: datetime
    expires_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class NotificationResponseSchema(BaseModel):
    """Notification response with ID."""

    id: str = Field(alias="_id")
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    source: NotificationSource
    is_read: bool
    created_at: str
    expires_at: str | None = None
    metadata: dict

    class Config:
        populate_by_name = True


class MarkReadSchema(BaseModel):
    """Schema for marking notification as read."""

    is_read: bool = True


class NotificationStatsSchema(BaseModel):
    """Notification statistics."""

    total_notifications: int
    unread_notifications: int
    critical_notifications: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
