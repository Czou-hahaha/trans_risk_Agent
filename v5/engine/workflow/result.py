"""Final workflow output schema."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from models.contribution import ContributionFinding
from models.conclusion import InvestigationConclusion
from models.investigation_timeline import InvestigationTimelineEvent
from models.metric_monitor import MetricMonitorFinding
from models.segment_stability import SegmentStabilityResult
from models.strategy_impact import StrategyImpactResult
from models.trend import TrendAnalysisResult


class InvestigationResult(BaseModel):
    investigation_id: str
    workflow_id: str
    metric_name: str
    analysis_date: date
    workflow_status: str
    needs_investigation: bool
    trigger_reason: str = ""
    executed_skills: list[str] = Field(default_factory=list)
    timeline: list[InvestigationTimelineEvent] = Field(default_factory=list)
    findings: list[dict] = Field(default_factory=list)
    executive_summary: str = ""
    generated_report_path: str | None = None
    monitor_finding: MetricMonitorFinding | None = None
    trend_result: TrendAnalysisResult | None = None
    contribution_findings: list[ContributionFinding] = Field(default_factory=list)
    segment_stability_result: SegmentStabilityResult | None = None
    strategy_impact_result: StrategyImpactResult | None = None
    investigation_conclusion: InvestigationConclusion | None = None
    generated_at: datetime
