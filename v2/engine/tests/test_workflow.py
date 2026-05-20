"""Workflow unit and integration tests."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text

_V1 = Path(__file__).resolve().parents[1]
if str(_V1) not in sys.path:
    sys.path.insert(0, str(_V1))

from models import (
    AttributionHint,
    ContributionFinding,
    InvestigationConclusion,
    InvestigationGate,
    MetricDirection,
    MetricMonitorFinding,
    MetricProfile,
    Severity,
)
from workflow.constants import REFERENCE_DATE
from workflow.runner import InvestigationWorkflowRunner
from workflow.status import WorkflowStatus


def _ts() -> datetime:
    return datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)


def _metric_finding(*, needs_investigation: bool = True) -> MetricMonitorFinding:
    return MetricMonitorFinding(
        finding_type="metric_monitor",
        metric_name="fpd7",
        summary="portfolio move",
        evidence={},
        generated_at=_ts(),
        metric_profile=MetricProfile.SHORT_TERM_RISK,
        current_value=0.052,
        previous_value=0.029,
        delta_pp=2.3,
        direction=MetricDirection.UP,
        investigation_gate=InvestigationGate.INVESTIGATE,
        needs_investigation=needs_investigation,
        is_abnormal=needs_investigation,
        severity=Severity.HIGH,
        attribution_hint=AttributionHint.RISK_DETERIORATION,
    )


def _contributor(contribution_pp: float = 0.455) -> ContributionFinding:
    return ContributionFinding(
        finding_type="dimension_contribution",
        metric_name="fpd7",
        summary="channel=partner_X",
        evidence={},
        generated_at=_ts(),
        dimension_name="channel",
        dimension_value="partner_X",
        current_value=4.1,
        previous_value=2.8,
        delta_pp=1.3,
        contribution_pp=contribution_pp,
        rank=1,
    )


def _conclusion() -> InvestigationConclusion:
    return InvestigationConclusion(
        conclusion_id="test-conclusion",
        metric_name="fpd7",
        risk_direction="deterioration",
        primary_driver="partner_X",
        secondary_drivers=[],
        business_summary="Driven by partner_X.",
        risk_hypothesis="Traffic quality weakened.",
        recommended_actions=["Review channel policy."],
        confidence=0.2,
        generated_at=_ts(),
    )


def test_completed_no_issue_short_circuits() -> None:
    runner = InvestigationWorkflowRunner("fpd7", workflow_id="wf-no-issue")
    with patch.object(runner, "run_monitor_stage", return_value=_metric_finding(needs_investigation=False)):
        result = runner.run()
    assert result.workflow_status == WorkflowStatus.COMPLETED_NO_ISSUE.value
    assert not result.needs_investigation
    assert result.contribution_findings == []


def test_full_pipeline_mocked() -> None:
    runner = InvestigationWorkflowRunner("fpd7")
    with (
        patch.object(runner, "run_monitor_stage", return_value=_metric_finding()),
        patch.object(runner, "run_contribution_stage", return_value=[_contributor()]),
        patch.object(runner, "run_summary_stage", return_value=_conclusion()),
    ):
        result = runner.run()
    assert result.workflow_status == WorkflowStatus.COMPLETED.value
    assert result.investigation_conclusion is not None


def _postgres_available() -> bool:
    try:
        from config.settings import settings

        engine = create_engine(settings.metric_monitor_database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


@pytest.mark.integration
def test_integration_full_workflow() -> None:
    if not _postgres_available():
        pytest.skip("PostgreSQL not available")
    with patch("services.llm.complete_synthesis", return_value=None):
        result = InvestigationWorkflowRunner("fpd7", reference_date=REFERENCE_DATE).run()
    assert result.workflow_status == WorkflowStatus.COMPLETED.value
    assert result.contribution_findings[0].dimension_value == "partner_X"
