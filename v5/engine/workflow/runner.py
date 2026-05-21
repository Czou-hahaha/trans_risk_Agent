"""Legacy runner — delegates to V4 InvestigationWorkflow."""

from __future__ import annotations

import logging
from datetime import date

from workflow.constants import DEFAULT_PERIOD_DAYS, REFERENCE_DATE
from workflow.context import WorkflowContext
from workflow.periods import resolve_period_windows
from workflow.result import InvestigationResult
from workflow.status import WorkflowStatus


def _workflow_class():
    from workflow.investigation_workflow import InvestigationWorkflow

    return InvestigationWorkflow

logger = logging.getLogger("investigation_workflow")


class InvestigationWorkflowRunner:
    """Backward-compatible facade over InvestigationWorkflow."""

    def __init__(
        self,
        metric_name: str,
        *,
        current_period: tuple[date, date] | None = None,
        previous_period: tuple[date, date] | None = None,
        reference_date: date | None = None,
        period_days: int = DEFAULT_PERIOD_DAYS,
        dimension_list: list[str] | None = None,
        top_n: int = 5,
        workflow_id: str | None = None,
    ) -> None:
        self._workflow = _workflow_class()(
            metric_name,
            analysis_date=reference_date or REFERENCE_DATE,
            current_period=current_period,
            previous_period=previous_period,
            period_days=period_days,
            dimension_list=dimension_list,
            top_n=top_n,
            investigation_id=workflow_id,
        )

    @property
    def context(self) -> WorkflowContext | None:
        ctx = self._workflow.context
        if ctx is None:
            return None
        return WorkflowContext(
            workflow_id=ctx.investigation_id,
            metric_name=ctx.metric_name,
            current_period=ctx.current_period,
            previous_period=ctx.previous_period,
            started_at=ctx.started_at,
            workflow_status=ctx.workflow_status,
            monitor_finding=ctx.monitor_finding,
            contribution_findings=ctx.contribution_findings,
            investigation_conclusion=ctx.investigation_conclusion,
            error_message=ctx.error_message,
            failed_stage=ctx.failed_stage,
        )

    def run(self) -> InvestigationResult:
        return self._workflow.execute()

    def run_monitor_stage(self):
        return self._workflow._run_metric_monitor()

    def run_contribution_stage(self):
        return self._workflow._run_dimension_contribution()

    def run_summary_stage(self):
        return self._workflow._run_finding_summary()

    def build_final_result(self) -> InvestigationResult:
        return self._workflow._build_result()
