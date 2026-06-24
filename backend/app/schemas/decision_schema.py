from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

DecisionSource = Literal["executive_pdf", "dashboard", "manual"]
DecisionPriority = Literal["low", "medium", "high", "critical"]
DecisionStatus = Literal["pending", "in_progress", "completed", "cancelled"]


class CreateDecisionSchema(BaseModel):
    decision_title: str = Field(..., min_length=1, max_length=300)
    decision_description: str = Field(default="", max_length=2000)
    decision_date: date | None = None
    source: DecisionSource = "manual"
    priority: DecisionPriority = "medium"
    expected_benefit: str = Field(default="", max_length=1000)
    created_from_analysis_id: str | None = None


class UpdateDecisionStatusSchema(BaseModel):
    status: DecisionStatus
