"""Pydantic schemas for company-level SaaS subscriptions (Sprint 9)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

SubscriptionStatus = Literal["trial", "active", "expired", "cancelled"]


class SubscriptionResponse(BaseModel):
    id: str
    company_id: str
    status: SubscriptionStatus
    plan_name: str
    plan_code: str
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    days_remaining: Optional[int] = None
    is_access_allowed: bool
    features: list[str] = Field(default_factory=list)
    price_mad: float = 0.0
    currency: str = "MAD"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SubscriptionStatusResponse(BaseModel):
    status: SubscriptionStatus
    is_access_allowed: bool
    days_remaining: Optional[int] = None
    message: Optional[str] = None
