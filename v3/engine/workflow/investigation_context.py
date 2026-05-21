"""Full investigation state across deterministic workflow stages."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from models.conclusion import InvestigationConclusion
from models.contribution import ContributionFinding
from models.metric_monitor import MetricMonitorFinding
from models.investigation_timeline import InvestigationTimelineEvent
from models.segment_stability import SegmentStabilityFinding, SegmentStabilityResult
from models.strategy_impact import StrategyImpactFinding, StrategyImpactResult
from models.trend import TrendAnalysisResult, TrendFinding
from workflow.investigation_state import WorkflowStatus
from workflow.workflow_router import WorkflowPlan


class InvestigationContext(BaseModel):
    investigation_id: str
    metric_name: str
    analysis_date: date
    trigger_reason: str = ""
    current_period: tuple[date, date]
    previous_period: tuple[date, date]
    started_at: datetime
    workflow_status: WorkflowStatus = WorkflowStatus.RUNNING
    plan: WorkflowPlan | None = None
    executed_skills: list[str] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[InvestigationTimelineEvent] = Field(default_factory=list)
    risk_summary: str = ""
    monitor_finding: MetricMonitorFinding | None = None
    trend_result: TrendAnalysisResult | None = None
    contribution_findings: list[ContributionFinding] = Field(default_factory=list)
    segment_stability_result: SegmentStabilityResult | None = None
    strategy_impact_result: StrategyImpactResult | None = None
    investigation_conclusion: InvestigationConclusion | None = None
    executive_summary: str = ""
    generated_report_path: str | None = None
    error_message: str | None = None
    failed_stage: str | None = None

    @property
    def trend_finding(self) -> TrendFinding | None:
        if self.trend_result is None:
            return None
        return self.trend_result.trend_finding

    @property
    def strategy_finding(self) -> StrategyImpactFinding | None:
        if not self.strategy_impact_result or not self.strategy_impact_result.findings:
            return None
        return self.strategy_impact_result.findings[0]

    @property
    def top_unstable_segments(self) -> list[SegmentStabilityFinding]:
        if self.segment_stability_result is None:
            return []
        return list(self.segment_stability_result.top_unstable_segments)
