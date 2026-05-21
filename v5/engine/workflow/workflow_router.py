"""Config-driven skill routing — no hardcoded trigger tables."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from models.contribution import ContributionFinding
from models.metric_monitor import MetricMonitorFinding
from models.segment_stability import SegmentStabilityFinding
from models.trend import TrendFinding
from workflow.workflow_rules import (
    WorkflowRuleConfig,
    load_investigation_workflow_config,
    load_workflow_rule_config,
    strategy_deployment_nearby,
)

if TYPE_CHECKING:
    from workflow_config.schemas.workflow_config_schema import InvestigationWorkflowConfig

logger = logging.getLogger(__name__)


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
    """Route analytics skills from monitor + intermediate findings (YAML-driven)."""

    def __init__(
        self,
        rule_config: WorkflowRuleConfig | None = None,
        *,
        workflow_config: InvestigationWorkflowConfig | None = None,
        config_root: str | None = None,
    ) -> None:
        self._wf = workflow_config or load_investigation_workflow_config(config_root)
        self._config = rule_config or load_workflow_rule_config(config_root)

    def plan_initial(
        self,
        monitor: MetricMonitorFinding,
        *,
        analysis_date: date,
    ) -> WorkflowPlan:
        plan = WorkflowPlan()
        anomaly = bool(monitor.needs_investigation)
        plan.metric_anomaly = anomaly

        if anomaly and self._fire_trigger("anomaly_detected", monitor=monitor):
            if self._should_run_skill("trend_analysis", "anomaly_detected", fired=True):
                plan.run_trend_analysis = True
            if self._should_run_skill(
                "dimension_contribution", "anomaly_detected", fired=True
            ):
                plan.run_dimension_contribution = True
            self._append_reason(plan, "anomaly_detected")

        if self._fire_trigger(
            "deployment_detected",
            analysis_date=analysis_date,
        ) and self._should_run_skill(
            "strategy_impact", "deployment_detected", fired=True
        ):
            plan.run_strategy_impact = True
            self._append_reason(plan, "deployment_detected")

        plan.always_finding_summary = self._wf.skill_enabled("finding_summary")
        plan.always_report_builder = (
            self._wf.skill_enabled("report_builder")
            and self._wf.skill_always_run("report_builder")
        )
        return plan

    def apply_trend(self, plan: WorkflowPlan, trend: TrendFinding | None) -> WorkflowPlan:
        if trend is None:
            return plan
        if not self._wf.skill_enabled("segment_stability"):
            return plan
        if self._trend_deterioration(trend) and self._should_run_skill(
            "segment_stability", "trend_deterioration", fired=True
        ):
            plan.run_segment_stability = True
            self._append_reason(plan, "trend_deterioration")
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
            if self._fire_trigger(
                "contributor_concentration", contributors=contributors
            ):
                plan.run_dimension_contribution = True
                self._append_reason(plan, "contributor_concentration")
        return plan

    def apply_segment_stability(
        self,
        plan: WorkflowPlan,
        segments: list[SegmentStabilityFinding],
    ) -> WorkflowPlan:
        unstable = [
            s
            for s in segments
            if s.segment_health in self._config.unstable_segment_health
        ]
        if unstable and self._fire_trigger("unstable_segment", segments=segments):
            self._append_reason(plan, "unstable_segment")
        return plan

    def _should_run_skill(
        self,
        skill_name: str,
        trigger_name: str,
        *,
        fired: bool,
    ) -> bool:
        if not self._wf.skill_enabled(skill_name):
            return False
        if self._wf.skill_always_run(skill_name):
            return True
        if not self._wf.skill_requires_trigger(skill_name, trigger_name):
            return False
        return fired

    def _fire_trigger(
        self,
        trigger_name: str,
        *,
        monitor: MetricMonitorFinding | None = None,
        analysis_date: date | None = None,
        trend: TrendFinding | None = None,
        contributors: list[ContributionFinding] | None = None,
        segments: list[SegmentStabilityFinding] | None = None,
    ) -> bool:
        definition = self._wf.triggers.triggers.get(trigger_name)
        if definition is None:
            logger.warning("Unknown workflow trigger: %s", trigger_name)
            return False

        if definition.evaluator == "strategy_deployment_nearby":
            if analysis_date is None:
                return False
            return strategy_deployment_nearby(
                analysis_date,
                self._config.default_strategy_deployment,
                window_days=self._config.strategy_nearby_days,
            )

        if definition.evaluator == "trend_upward_deterioration":
            return trend is not None and self._trend_deterioration(trend)

        if definition.evaluator == "top_contributor_concentration":
            if not contributors:
                return False
            top = max(contributors, key=lambda c: abs(c.contribution_pp))
            return abs(top.contribution_pp) >= self._config.contributor_concentration_pp

        if definition.evaluator == "unstable_segment_health":
            return any(
                s.segment_health in self._config.unstable_segment_health
                for s in (segments or [])
            )

        if definition.evaluator == "has_contributors":
            return bool(contributors)

        if definition.field == "needs_investigation" and monitor is not None:
            return bool(monitor.needs_investigation)

        return False

    def _trend_deterioration(self, trend: TrendFinding) -> bool:
        return (
            trend.trend_direction in self._config.trend_deterioration_directions
            and trend.trend_strength in self._config.trend_deterioration_strengths
        )

    def _append_reason(self, plan: WorkflowPlan, trigger_name: str) -> None:
        reason = self._wf.trigger_reason(trigger_name)
        if reason not in plan.trigger_reasons:
            plan.trigger_reasons.append(reason)
