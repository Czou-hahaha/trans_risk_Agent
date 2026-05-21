"""Deterministic skill routing — no LLM / agent planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from models.contribution import ContributionFinding
from models.metric_monitor import MetricMonitorFinding
from models.segment_stability import SegmentStabilityFinding
from models.trend import TrendFinding
from workflow.workflow_rules import WorkflowRuleConfig, strategy_deployment_nearby


@dataclass
class WorkflowPlan:
    """Ordered skills to execute after metric_monitor."""

    metric_anomaly: bool = False
    run_trend_analysis: bool = False
    run_dimension_contribution: bool = False
    run_segment_stability: bool = False
    run_strategy_impact: bool = False
    always_finding_summary: bool = True
    always_report_builder: bool = True
    trigger_reasons: list[str] = field(default_factory=list)

    @property
    def downstream_skills(self) -> list[str]:
        skills: list[str] = []
        if self.run_trend_analysis:
            skills.append("trend_analysis")
        if self.run_dimension_contribution:
            skills.append("dimension_contribution")
        if self.run_segment_stability:
            skills.append("segment_stability")
        if self.run_strategy_impact:
            skills.append("strategy_impact")
        if self.always_finding_summary:
            skills.append("finding_summary")
        if self.always_report_builder:
            skills.append("report_builder")
        return skills

    @property
    def executed_skills(self) -> list[str]:
        return ["metric_monitor", *self.downstream_skills]


class WorkflowRouter:
    """Route analytics skills from monitor + intermediate findings."""

    def __init__(self, config: WorkflowRuleConfig | None = None) -> None:
        self._config = config or WorkflowRuleConfig()

    def plan_initial(
        self,
        monitor: MetricMonitorFinding,
        *,
        analysis_date: date,
    ) -> WorkflowPlan:
        anomaly = bool(monitor.needs_investigation)
        plan = WorkflowPlan(metric_anomaly=anomaly)

        if anomaly:
            plan.run_trend_analysis = True
            plan.run_dimension_contribution = True
            plan.trigger_reasons.append("metric_anomaly")

        if strategy_deployment_nearby(
            analysis_date,
            self._config.default_strategy_deployment,
            window_days=self._config.strategy_nearby_days,
        ):
            plan.run_strategy_impact = True
            plan.trigger_reasons.append("strategy_deployment_nearby")

        return plan

    def apply_trend(self, plan: WorkflowPlan, trend: TrendFinding | None) -> WorkflowPlan:
        if trend is None:
            return plan
        if trend.trend_direction in {"upward"} and trend.trend_strength in {
            "moderate",
            "strong",
            "weak",
        }:
            if trend.trend_direction == "upward":
                plan.run_segment_stability = True
                if "trend_deterioration" not in plan.trigger_reasons:
                    plan.trigger_reasons.append("trend_deterioration")
        return plan

    def apply_contribution(
        self,
        plan: WorkflowPlan,
        contributors: list[ContributionFinding],
    ) -> WorkflowPlan:
        if not contributors:
            return plan
        top = max(contributors, key=lambda c: abs(c.contribution_pp))
        if abs(top.contribution_pp) >= self._config.contributor_concentration_pp:
            plan.run_dimension_contribution = True
            if "contributor_concentration" not in plan.trigger_reasons:
                plan.trigger_reasons.append("contributor_concentration")
        return plan

    def apply_segment_stability(
        self,
        plan: WorkflowPlan,
        segments: list[SegmentStabilityFinding],
    ) -> WorkflowPlan:
        unstable = [
            s
            for s in segments
            if s.segment_health in {"unstable", "deteriorating"}
        ]
        if unstable and "unstable_segment" not in plan.trigger_reasons:
            plan.trigger_reasons.append("unstable_segment_detected")
        return plan
