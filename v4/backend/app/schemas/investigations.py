"""API schemas for investigations."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateInvestigationRequest(BaseModel):
    goal: str = Field(min_length=1, examples=["分析本周FPD7上升原因"])
    metric_name: Optional[str] = Field(default=None, description="Override parsed metric")
    analysis_date: Optional[date] = Field(
        default=None, description="Reference date for analytics window"
    )


class RunInvestigationRequest(BaseModel):
    metric_name: str = Field(default="fpd7", examples=["fpd7"])
    analysis_date: str = Field(default="2026-05-20", examples=["2026-05-20"])
    goal: Optional[str] = Field(default=None)


class InvestigationStepOut(BaseModel):
    id: UUID
    step_name: str
    step_order: int
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    output_preview: Optional[str]
    output_json: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class InvestigationListItem(BaseModel):
    id: UUID
    goal: str
    metric_name: str
    workflow_id: str
    status: str
    needs_investigation: Optional[bool]
    created_at: datetime
    updated_at: datetime
    report_id: Optional[UUID] = None

    model_config = {"from_attributes": True}


class InvestigationDetailOut(BaseModel):
    id: UUID
    goal: str
    metric_name: str
    analysis_date: Optional[date] = None
    workflow_id: str
    status: str
    needs_investigation: Optional[bool]
    error_message: Optional[str]
    failed_stage: Optional[str]
    created_at: datetime
    updated_at: datetime
    steps: list[InvestigationStepOut]
    report_id: Optional[UUID] = None
    executive_summary: Optional[str] = None
    executed_skills: Optional[list[str]] = None

    model_config = {"from_attributes": True}


class DashboardKpis(BaseModel):
    total_investigations: int
    running_investigations: int
    completed_investigations: int
    failed_investigations: int


class RiskAlertItem(BaseModel):
    id: str
    metric_name: str
    summary: str
    severity: str
    created_at: datetime


class DashboardOut(BaseModel):
    kpis: DashboardKpis
    latest_investigations: list[InvestigationListItem]
    latest_risk_alerts: list[RiskAlertItem]
    latest_reports: list[InvestigationListItem]
