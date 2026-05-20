"""Deterministic investigation workflow: monitor → contribution → summary."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

_V1 = Path(__file__).resolve().parents[1]
if str(_V1) not in sys.path:
    sys.path.insert(0, str(_V1))

from models.contribution import ContributionFinding
from models.conclusion import InvestigationConclusion
from models.metric_monitor import MetricMonitorFinding
from skill_runtime.dimension_contribution import DimensionContributionSkill
from skill_runtime.finding_summary import FindingSummarySkill
from skill_runtime.metric_monitor import MetricMonitorSkill
from tools.db.contribution.session import SessionLocal as ContributionSession
from tools.db.monitor.session import SessionLocal as MonitorSession
from workflow.constants import (
    DEFAULT_DIMENSIONS,
    DEFAULT_PERIOD_DAYS,
    DEFAULT_TOP_N,
    REFERENCE_DATE,
)
from workflow.context import WorkflowContext
from workflow.result import InvestigationResult
from workflow.status import WorkflowStatus

logger = logging.getLogger("investigation_workflow")
T = TypeVar("T")


def resolve_period_windows(
    *,
    reference_date: date,
    period_days: int = DEFAULT_PERIOD_DAYS,
) -> tuple[tuple[date, date], tuple[date, date]]:
    def _window(days_back_end: int, length: int) -> tuple[date, date]:
        end = reference_date - timedelta(days=days_back_end)
        start = end - timedelta(days=length - 1)
        return start, end

    return _window(0, period_days), _window(period_days, period_days)


class InvestigationWorkflowRunner:
    """Pipeline coordinator — no SQL, metric math, or LLM logic here."""

    def __init__(
        self,
        metric_name: str,
        *,
        current_period: tuple[date, date] | None = None,
        previous_period: tuple[date, date] | None = None,
        reference_date: date | None = None,
        period_days: int = DEFAULT_PERIOD_DAYS,
        dimension_list: list[str] | None = None,
        top_n: int = DEFAULT_TOP_N,
        workflow_id: str | None = None,
    ) -> None:
        ref = reference_date or REFERENCE_DATE
        if current_period is None or previous_period is None:
            cur, prev = resolve_period_windows(reference_date=ref, period_days=period_days)
            current_period = current_period or cur
            previous_period = previous_period or prev

        self._metric_name = metric_name
        self._current_period = current_period
        self._previous_period = previous_period
        self._dimension_list = dimension_list or list(DEFAULT_DIMENSIONS)
        self._top_n = top_n
        self._workflow_id = workflow_id
        self._context: WorkflowContext | None = None

    @property
    def context(self) -> WorkflowContext | None:
        return self._context

    def run(self) -> InvestigationResult:
        self._context = WorkflowContext(
            workflow_id=self._workflow_id or str(uuid4()),
            metric_name=self._metric_name,
            current_period=self._current_period,
            previous_period=self._previous_period,
            started_at=datetime.now(timezone.utc),
            workflow_status=WorkflowStatus.RUNNING,
        )
        try:
            logger.info("[Workflow] Starting monitor stage...")
            self._context.monitor_finding = self._invoke_stage(
                "monitor", self.run_monitor_stage
            )
            if not self._context.monitor_finding.needs_investigation:
                self._context.workflow_status = WorkflowStatus.COMPLETED_NO_ISSUE
                logger.info("[Workflow] Investigation completed (no issue).")
                return self.build_final_result()

            logger.info("[Workflow] Running contribution analysis...")
            self._context.contribution_findings = self._invoke_stage(
                "contribution", self.run_contribution_stage
            )
            logger.info("[Workflow] Generating investigation summary...")
            self._context.investigation_conclusion = self._invoke_stage(
                "summary", self.run_summary_stage
            )
            self._context.workflow_status = WorkflowStatus.COMPLETED
            logger.info("[Workflow] Investigation completed.")
            return self.build_final_result()
        except Exception as exc:
            logger.error(
                "[Workflow] Stage failed stage=%s error=%s",
                self._context.failed_stage,
                exc,
                exc_info=True,
            )
            self._context.workflow_status = WorkflowStatus.FAILED
            self._context.error_message = str(exc)
            return self.build_final_result()

    def _invoke_stage(self, stage_name: str, stage_fn: Callable[[], T]) -> T:
        assert self._context is not None
        self._context.failed_stage = stage_name
        return stage_fn()

    def run_monitor_stage(self) -> MetricMonitorFinding:
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

    def run_contribution_stage(self) -> list[ContributionFinding]:
        with ContributionSession() as session:
            result = DimensionContributionSkill(session).run(
                metric_name=self._metric_name,
                current_period=self._current_period,
                previous_period=self._previous_period,
                dimension_list=self._dimension_list,
                top_n=self._top_n,
            )
        return list(result.top_contributors)

    def run_summary_stage(self) -> InvestigationConclusion:
        assert self._context and self._context.monitor_finding
        if not self._context.contribution_findings:
            raise ValueError("contribution_findings required before summary stage")
        return FindingSummarySkill().run(
            self._context.monitor_finding,
            self._context.contribution_findings,
        )

    def build_final_result(self) -> InvestigationResult:
        assert self._context is not None
        monitor = self._context.monitor_finding
        needs = bool(monitor.needs_investigation) if monitor else False
        return InvestigationResult(
            workflow_id=self._context.workflow_id,
            metric_name=self._context.metric_name,
            workflow_status=self._context.workflow_status.value,
            needs_investigation=needs,
            monitor_finding=monitor,
            contribution_findings=self._context.contribution_findings,
            investigation_conclusion=self._context.investigation_conclusion,
            generated_at=datetime.now(timezone.utc),
        )
