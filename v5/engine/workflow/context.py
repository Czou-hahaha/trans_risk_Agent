"""Workflow state across pipeline stages."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from models.contribution import ContributionFinding
from models.conclusion import InvestigationConclusion
from models.metric_monitor import MetricMonitorFinding
from workflow.status import WorkflowStatus


class WorkflowContext(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    metric_name: str
    current_period: tuple[date, date]
    previous_period: tuple[date, date]
    started_at: datetime
    workflow_status: WorkflowStatus = WorkflowStatus.RUNNING
    monitor_finding: MetricMonitorFinding | None = None
    contribution_findings: list[ContributionFinding] = Field(default_factory=list)
    investigation_conclusion: InvestigationConclusion | None = None
    error_message: str | None = None
    failed_stage: str | None = None
