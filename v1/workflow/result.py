"""Final workflow output schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from models.contribution import ContributionFinding
from models.conclusion import InvestigationConclusion
from models.metric_monitor import MetricMonitorFinding


class InvestigationResult(BaseModel):
    workflow_id: str
    metric_name: str
    workflow_status: str
    needs_investigation: bool
    monitor_finding: MetricMonitorFinding | None = None
    contribution_findings: list[ContributionFinding] = Field(default_factory=list)
    investigation_conclusion: InvestigationConclusion | None = None
    generated_at: datetime
