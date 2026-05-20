"""API schemas for investigations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateInvestigationRequest(BaseModel):
    goal: str = Field(min_length=1, examples=["分析本周FPD7上升原因"])
    metric_name: Optional[str] = Field(default=None, description="Override parsed metric")


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
    workflow_id: str
    status: str
    needs_investigation: Optional[bool]
    error_message: Optional[str]
    failed_stage: Optional[str]
    created_at: datetime
    updated_at: datetime
    steps: list[InvestigationStepOut]
    report_id: Optional[UUID] = None

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
