"""API schemas for investigation reports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ContributorRankingItem(BaseModel):
    rank: int
    dimension_name: str
    dimension_value: str
    contribution_pp: float
    delta_pp: float


class ReportOut(BaseModel):
    id: UUID
    investigation_id: UUID
    goal: str
    metric_name: str
    workflow_status: str
    business_summary: str
    risk_hypothesis: str
    recommended_actions: list[str]
    contributor_ranking: list[ContributorRankingItem]
    monitor_finding: Optional[Dict[str, Any]] = None
    executive_summary: str = ""
    executed_skills: list[str] = Field(default_factory=list)
    timeline: list[Dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime
    markdown_export: str

    model_config = {"from_attributes": True}
