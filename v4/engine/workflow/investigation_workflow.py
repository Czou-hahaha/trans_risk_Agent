"""V4 deterministic investigation orchestration — full analytics pipeline."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import TypeVar
from uuid import uuid4

from models.contribution import ContributionFinding
from models.conclusion import InvestigationConclusion
from models.exceptions import (
    BreakdownDataNotFoundError,
    MetricDataNotFoundError,
    StrategyDataNotFoundError,
)
from models.metric_monitor import MetricMonitorFinding
from models.investigation_timeline import InvestigationTimelineEvent, SkillName
from skill_runtime.dimension_contribution import DimensionContributionSkill
from skill_runtime.finding_summary import FindingSummarySkill
from skill_runtime.metric_monitor import MetricMonitorSkill
from skill_runtime.segment_stability import SegmentStabilitySkill
from skill_runtime.strategy_impact import StrategyImpactSkill
from skill_runtime.trend_analysis import TrendAnalysisSkill
from tools.db.contribution.session import SessionLocal as ContributionSession
from tools.db.monitor.session import SessionLocal as MonitorSession
from workflow.constants import (
    DEFAULT_DIMENSIONS,
    DEFAULT_PERIOD_DAYS,
    DEFAULT_TOP_N,
    REFERENCE_DATE,
)
from workflow.investigation_context import InvestigationContext
from workflow.investigation_state import SkillExecutionStatus, WorkflowStatus
from workflow.result import InvestigationResult
from workflow.periods import resolve_period_windows
from workflow.workflow_router import WorkflowRouter
from workflow.workflow_rules import WorkflowRuleConfig

logger = logging.getLogger("investigation_workflow")
T = TypeVar("T")


class InvestigationWorkflow:
    """Deterministic skill sequencing, routing, aggregation, and report generation."""

    def __init__(
        self,
        metric_name: str,
        *,
        analysis_date: date | None = None,
        current_period: tuple[date, date] | None = None,
        previous_period: tuple[date, date] | None = None,
        period_days: int = DEFAULT_PERIOD_DAYS,
        dimension_list: list[str] | None = None,
        top_n: int = DEFAULT_TOP_N,
        investigation_id: str | None = None,
        router: WorkflowRouter | None = None,
        rule_config: WorkflowRuleConfig | None = None,
    ) -> None:
        ref = analysis_date or REFERENCE_DATE
        if current_period is None or previous_period is None:
            cur, prev = resolve_period_windows(reference_date=ref, period_days=period_days)
            current_period = current_period or cur
            previous_period = previous_period or prev

        self._metric_name = metric_name
        self._analysis_date = ref
        self._current_period = current_period
        self._previous_period = previous_period
        self._dimension_list = dimension_list or list(DEFAULT_DIMENSIONS)
        self._top_n = top_n
        self._investigation_id = investigation_id or str(uuid4())
        self._router = router or WorkflowRouter(rule_config)
        self._rule_config = rule_config or WorkflowRuleConfig()
        self._ctx: InvestigationContext | None = None

    @classmethod
    def run(
        cls,
        metric_name: str,
        analysis_date: date | str | None = None,
        **kwargs: object,
    ) -> InvestigationResult:
        if isinstance(analysis_date, str):
            analysis_date = date.fromisoformat(analysis_date)
        return cls(metric_name, analysis_date=analysis_date, **kwargs).execute()

    @property
    def context(self) -> InvestigationContext | None:
        return self._ctx

    def execute(self) -> InvestigationResult:
        self._ctx = InvestigationContext(
            investigation_id=self._investigation_id,
            metric_name=self._metric_name,
            analysis_date=self._analysis_date,
            current_period=self._current_period,
            previous_period=self._previous_period,
            started_at=datetime.now(timezone.utc),
            workflow_status=WorkflowStatus.RUNNING,
        )
        try:
            monitor = self._run_skill(
                "metric_monitor",
                self._run_metric_monitor,
                step_order=1,
            )
            self._ctx.monitor_finding = monitor
            self._append_finding(monitor)
            self._ctx.plan = self._router.plan_initial(
                monitor, analysis_date=self._analysis_date
            )
            self._ctx.trigger_reason = ", ".join(self._ctx.plan.trigger_reasons)

            if not monitor.needs_investigation:
                self._ctx.workflow_status = WorkflowStatus.COMPLETED_NO_ISSUE
                self._ctx.risk_summary = monitor.summary
                from report.investigation_report_builder import InvestigationReportBuilder

                self._ctx.executive_summary = (
                    InvestigationReportBuilder().generate_executive_summary(self._ctx)
                )
                self._run_skill(
                    "report_builder",
                    self._run_report_builder,
                    step_order=99,
                    allow_skip=False,
                )
                return self._build_result()

            plan = self._ctx.plan

            if plan.run_trend_analysis:
                try:
                    trend_result = self._run_skill(
                        "trend_analysis",
                        self._run_trend_analysis,
                        step_order=2,
                    )
                    self._ctx.trend_result = trend_result
                    self._append_finding(trend_result.trend_finding)
                    plan = self._router.apply_trend(plan, trend_result.trend_finding)
                except MetricDataNotFoundError:
                    plan = self._router.apply_trend(plan, None)

            if plan.run_dimension_contribution:
                contributors = self._run_skill(
                    "dimension_contribution",
                    self._run_dimension_contribution,
                    step_order=3,
                )
                self._ctx.contribution_findings = contributors
                for c in contributors:
                    self._append_finding(c)
                plan = self._router.apply_contribution(plan, contributors)

            if plan.run_segment_stability or self._ctx.trend_finding:
                try:
                    seg_result = self._run_skill(
                        "segment_stability",
                        self._run_segment_stability,
                        step_order=4,
                    )
                    self._ctx.segment_stability_result = seg_result
                    for seg in seg_result.top_unstable_segments:
                        self._append_finding(seg)
                    plan = self._router.apply_segment_stability(
                        plan, seg_result.top_unstable_segments
                    )
                except BreakdownDataNotFoundError:
                    pass

            if plan.run_strategy_impact:
                try:
                    strat_result = self._run_skill(
                        "strategy_impact",
                        self._run_strategy_impact,
                        step_order=5,
                    )
                    self._ctx.strategy_impact_result = strat_result
                    for f in strat_result.findings:
                        self._append_finding(f)
                except StrategyDataNotFoundError:
                    pass

            if plan.always_finding_summary and self._ctx.contribution_findings:
                conclusion = self._run_skill(
                    "finding_summary",
                    self._run_finding_summary,
                    step_order=6,
                )
                self._ctx.investigation_conclusion = conclusion

            if plan.always_report_builder:
                self._run_skill(
                    "report_builder",
                    self._run_report_builder,
                    step_order=7,
                )

            self._ctx.workflow_status = WorkflowStatus.COMPLETED
            if not self._ctx.executive_summary and monitor:
                from report.investigation_report_builder import InvestigationReportBuilder

                self._ctx.executive_summary = (
                    InvestigationReportBuilder().generate_executive_summary(self._ctx)
                )
            self._ctx.risk_summary = self._ctx.executive_summary or monitor.summary
            return self._build_result()

        except Exception as exc:
            logger.error(
                "Investigation failed stage=%s: %s",
                self._ctx.failed_stage if self._ctx else None,
                exc,
                exc_info=True,
            )
            if self._ctx:
                self._ctx.workflow_status = WorkflowStatus.FAILED
                self._ctx.error_message = str(exc)
            return self._build_result()

    def _run_skill(
        self,
        skill_name: SkillName,
        fn: Callable[[], T],
        *,
        step_order: int,
        allow_skip: bool = True,
    ) -> T:
        assert self._ctx is not None
        self._ctx.failed_stage = skill_name
        started = time.perf_counter()
        ts = datetime.now(timezone.utc)
        self._timeline(skill_name, "running", "Started", ts, step_order)
        try:
            result = fn()
            duration = int((time.perf_counter() - started) * 1000)
            summary = _skill_summary(skill_name, result)
            self._timeline(
                skill_name, "completed", summary, ts, step_order, duration
            )
            if skill_name not in self._ctx.executed_skills:
                self._ctx.executed_skills.append(skill_name)
            return result
        except Exception as exc:
            duration = int((time.perf_counter() - started) * 1000)
            if allow_skip and _is_skippable(exc):
                self._timeline(
                    skill_name, "skipped", str(exc), ts, step_order, duration
                )
                raise
            self._timeline(
                skill_name, "failed", str(exc), ts, step_order, duration
            )
            raise

    def _record_skipped(
        self, skill_name: SkillName, message: str, *, step_order: int
    ) -> None:
        assert self._ctx is not None
        self._timeline(
            skill_name,
            "skipped",
            message,
            datetime.now(timezone.utc),
            step_order,
        )

    def _timeline(
        self,
        skill_name: SkillName,
        status: str,
        summary: str,
        timestamp: datetime,
        step_order: int,
        duration_ms: int | None = None,
    ) -> None:
        assert self._ctx is not None
        self._ctx.timeline.append(
            InvestigationTimelineEvent(
                timestamp=timestamp,
                skill_name=skill_name,
                execution_status=status,  # type: ignore[arg-type]
                summary=summary,
                duration_ms=duration_ms,
                step_order=step_order,
            )
        )

    def _append_finding(self, finding: object) -> None:
        assert self._ctx is not None
        if hasattr(finding, "model_dump"):
            self._ctx.findings.append(finding.model_dump(mode="json"))  # type: ignore[union-attr]

    def _run_metric_monitor(self) -> MetricMonitorFinding:
        cur_s, cur_e = self._current_period
        prev_s, prev_e = self._previous_period
        with MonitorSession() as session:
            return MetricMonitorSkill(session).run(
                metric_name=self._metric_name,
                current_start_date=cur_s,
                current_end_date=cur_e,
                previous_start_date=prev_s,
                previous_end_date=prev_e,
            )

    def _run_trend_analysis(self):
        with MonitorSession() as mon, ContributionSession() as contrib:
            return TrendAnalysisSkill(mon, contrib).run(
                metric_name=self._metric_name,
                end_date=self._analysis_date,
            )

    def _run_dimension_contribution(self) -> list[ContributionFinding]:
        with ContributionSession() as session:
            result = DimensionContributionSkill(session).run(
                metric_name=self._metric_name,
                current_period=self._current_period,
                previous_period=self._previous_period,
                dimension_list=self._dimension_list,
                top_n=self._top_n,
            )
        return list(result.top_contributors)

    def _run_segment_stability(self):
        with ContributionSession() as session:
            return SegmentStabilitySkill(session).run(
                metric_name=self._metric_name,
                dimension_name="channel",
                end_date=self._analysis_date,
            )

    def _run_strategy_impact(self):
        with MonitorSession() as session:
            return StrategyImpactSkill(session).run(
                strategy_name=self._rule_config.default_strategy_name,
                deployment_date=self._rule_config.default_strategy_deployment,
            )

    def _run_finding_summary(self) -> InvestigationConclusion:
        assert self._ctx and self._ctx.monitor_finding
        return FindingSummarySkill().run(
            self._ctx.monitor_finding,
            self._ctx.contribution_findings,
        )

    def _run_report_builder(self) -> str:
        from report.investigation_report_builder import InvestigationReportBuilder

        assert self._ctx is not None
        _, markdown, _ = InvestigationReportBuilder().build(self._ctx)
        if "report_builder" not in self._ctx.executed_skills:
            self._ctx.executed_skills.append("report_builder")
        return markdown

    def _build_result(self) -> InvestigationResult:
        assert self._ctx is not None
        monitor = self._ctx.monitor_finding
        needs = bool(monitor.needs_investigation) if monitor else False
        return InvestigationResult(
            investigation_id=self._ctx.investigation_id,
            workflow_id=self._ctx.investigation_id,
            metric_name=self._ctx.metric_name,
            analysis_date=self._ctx.analysis_date,
            workflow_status=self._ctx.workflow_status.value,
            needs_investigation=needs,
            trigger_reason=self._ctx.trigger_reason,
            executed_skills=list(self._ctx.executed_skills),
            timeline=list(self._ctx.timeline),
            findings=list(self._ctx.findings),
            executive_summary=self._ctx.executive_summary,
            generated_report_path=self._ctx.generated_report_path,
            monitor_finding=monitor,
            trend_result=self._ctx.trend_result,
            contribution_findings=self._ctx.contribution_findings,
            segment_stability_result=self._ctx.segment_stability_result,
            strategy_impact_result=self._ctx.strategy_impact_result,
            investigation_conclusion=self._ctx.investigation_conclusion,
            generated_at=datetime.now(timezone.utc),
        )


def _is_skippable(exc: Exception) -> bool:
    return isinstance(
        exc,
        (MetricDataNotFoundError, BreakdownDataNotFoundError, StrategyDataNotFoundError),
    )


def _skill_summary(skill_name: str, result: object) -> str:
    if skill_name == "metric_monitor" and hasattr(result, "summary"):
        return str(result.summary)[:200]
    if skill_name == "trend_analysis" and hasattr(result, "trend_finding"):
        return str(result.trend_finding.summary)[:200]
    if skill_name == "dimension_contribution" and isinstance(result, list):
        return f"{len(result)} contributors ranked"
    if skill_name == "segment_stability" and hasattr(result, "top_unstable_segments"):
        n = len(result.top_unstable_segments)
        return f"{n} segments reviewed"
    if skill_name == "strategy_impact" and hasattr(result, "findings") and result.findings:
        return str(result.findings[0].summary)[:200]
    if skill_name == "finding_summary" and hasattr(result, "business_summary"):
        return str(result.business_summary)[:200]
    if skill_name == "report_builder":
        return "Markdown report generated"
    return "completed"
