"""V4 investigation workflow tests."""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ENGINE = Path(__file__).resolve().parents[1]
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

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
from models.segment_stability import SegmentStabilityFinding, SegmentStabilityResult
from models.strategy_impact import StrategyImpactFinding, StrategyImpactResult
from models.trend import TrendAnalysisResult, TrendFinding
from report.investigation_report_builder import InvestigationReportBuilder
from workflow.investigation_workflow import InvestigationWorkflow
from workflow.status import WorkflowStatus
from workflow.workflow_router import WorkflowRouter


def _ts() -> datetime:
    return datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc)


def _monitor(*, needs: bool = True) -> MetricMonitorFinding:
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
        needs_investigation=needs,
        is_abnormal=needs,
        severity=Severity.HIGH,
        attribution_hint=AttributionHint.RISK_DETERIORATION,
    )


def _contributor() -> ContributionFinding:
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
        contribution_pp=0.55,
        rank=1,
    )


def _trend() -> TrendAnalysisResult:
    finding = TrendFinding(
        finding_type="trend_analysis",
        metric_name="fpd7",
        summary="FPD7 upward trend",
        evidence={},
        generated_at=_ts(),
        trend_direction="upward",
        trend_strength="moderate",
        rolling_change_pp=1.2,
        slope_value=0.001,
        volatility_score=0.1,
        volatility_level="low",
        consecutive_up_periods=3,
        anomaly_periods=[],
        current_value=0.05,
        baseline_value=0.04,
    )
    return TrendAnalysisResult(
        metric_name="fpd7",
        analysis_window_days=60,
        aggregation_level="week",
        trend_finding=finding,
        generated_at=_ts(),
    )


def _segments() -> SegmentStabilityResult:
    seg = SegmentStabilityFinding(
        finding_type="segment_stability",
        metric_name="fpd7",
        summary="partner_X unstable",
        evidence={},
        generated_at=_ts(),
        dimension_name="channel",
        dimension_value="partner_X",
        stability_score=0.3,
        volatility_score=0.2,
        volatility_level="high",
        trend_direction="upward",
        consecutive_up_periods=4,
        regime_shift_detected=True,
        segment_health="unstable",
        current_metric_value=0.08,
        baseline_metric_value=0.04,
    )
    return SegmentStabilityResult(
        metric_name="fpd7",
        dimension_name="channel",
        analysis_window_days=60,
        top_unstable_segments=[seg],
        generated_at=_ts(),
    )


def _strategy() -> StrategyImpactResult:
    finding = StrategyImpactFinding(
        finding_type="strategy_impact",
        metric_name="strategy_impact",
        summary="strategy effective",
        evidence={},
        generated_at=_ts(),
        strategy_name="RISK_003",
        deployment_date=date(2026, 5, 10),
        before_window_days=14,
        after_window_days=14,
        approval_rate_before=0.65,
        approval_rate_after=0.618,
        approval_delta_pp=-3.2,
        fpd7_before=0.05,
        fpd7_after=0.039,
        fpd7_delta_pp=-1.1,
        volume_before=10000,
        volume_after=9150,
        volume_delta_pct=-8.5,
        risk_reduction_efficiency=0.34,
        strategy_effectiveness="effective",
    )
    return StrategyImpactResult(
        strategy_name="RISK_003",
        deployment_date=date(2026, 5, 10),
        findings=[finding],
        generated_at=_ts(),
    )


def _conclusion() -> InvestigationConclusion:
    return InvestigationConclusion(
        conclusion_id="c1",
        metric_name="fpd7",
        risk_direction="deterioration",
        primary_driver="partner_X",
        secondary_drivers=[],
        business_summary="Driven by partner_X.",
        risk_hypothesis="Traffic quality weakened.",
        recommended_actions=["Review channel policy."],
        confidence=0.5,
        generated_at=_ts(),
    )


class TestWorkflowRouter:
    def test_plan_on_anomaly(self) -> None:
        plan = WorkflowRouter().plan_initial(
            _monitor(), analysis_date=date(2026, 5, 20)
        )
        assert plan.metric_anomaly
        assert plan.run_trend_analysis
        assert plan.run_dimension_contribution
        assert "metric_anomaly" in plan.trigger_reasons

    def test_strategy_nearby(self) -> None:
        plan = WorkflowRouter().plan_initial(
            _monitor(needs=False), analysis_date=date(2026, 5, 20)
        )
        assert plan.run_strategy_impact


class TestInvestigationReportBuilder:
    def test_executive_summary(self) -> None:
        from workflow.investigation_context import InvestigationContext
        from workflow.workflow_router import WorkflowPlan

        ctx = InvestigationContext(
            investigation_id="inv-1",
            metric_name="fpd7",
            analysis_date=date(2026, 5, 20),
            current_period=(date(2026, 5, 14), date(2026, 5, 20)),
            previous_period=(date(2026, 5, 7), date(2026, 5, 13)),
            started_at=_ts(),
            monitor_finding=_monitor(),
            contribution_findings=[_contributor()],
            plan=WorkflowPlan(),
        )
        summary = InvestigationReportBuilder().generate_executive_summary(ctx)
        assert "partner_X" in summary
        assert "FPD7" in summary or "fpd7" in summary.lower()


class TestInvestigationWorkflow:
    @patch.object(InvestigationWorkflow, "_run_metric_monitor")
    def test_no_issue_short_circuit(self, mock_monitor: MagicMock) -> None:
        mock_monitor.return_value = _monitor(needs=False)
        with patch.object(InvestigationWorkflow, "_run_report_builder", return_value="# Report"):
            result = InvestigationWorkflow.run(
                "fpd7", analysis_date=date(2026, 5, 20), investigation_id="wf-1"
            )
        assert result.workflow_status == WorkflowStatus.COMPLETED_NO_ISSUE.value
        assert "metric_monitor" in result.executed_skills
        assert result.executive_summary

    @patch.object(InvestigationWorkflow, "_run_finding_summary")
    @patch.object(InvestigationWorkflow, "_run_strategy_impact")
    @patch.object(InvestigationWorkflow, "_run_segment_stability")
    @patch.object(InvestigationWorkflow, "_run_dimension_contribution")
    @patch.object(InvestigationWorkflow, "_run_trend_analysis")
    @patch.object(InvestigationWorkflow, "_run_metric_monitor")
    def test_full_workflow_mocked(
        self,
        mock_monitor: MagicMock,
        mock_trend: MagicMock,
        mock_contrib: MagicMock,
        mock_segment: MagicMock,
        mock_strategy: MagicMock,
        mock_summary: MagicMock,
    ) -> None:
        mock_monitor.return_value = _monitor()
        mock_trend.return_value = _trend()
        mock_contrib.return_value = [_contributor()]
        mock_segment.return_value = _segments()
        mock_strategy.return_value = _strategy()
        mock_summary.return_value = _conclusion()

        result = InvestigationWorkflow.run(
            "fpd7", analysis_date="2026-05-20", investigation_id="wf-full"
        )

        assert result.workflow_status == WorkflowStatus.COMPLETED.value
        assert "trend_analysis" in result.executed_skills
        assert "dimension_contribution" in result.executed_skills
        assert len(result.timeline) >= 5
        assert result.executive_summary
        assert result.findings
        assert result.generated_report_path

    @patch.object(InvestigationWorkflow, "_run_metric_monitor")
    def test_timeline_records_duration(self, mock_monitor: MagicMock) -> None:
        mock_monitor.return_value = _monitor(needs=False)
        with patch.object(InvestigationWorkflow, "_run_report_builder", return_value="md"):
            result = InvestigationWorkflow.run("fpd7", analysis_date=date(2026, 5, 20))
        monitor_events = [
            e for e in result.timeline if e.skill_name == "metric_monitor"
        ]
        assert monitor_events
        assert any(e.execution_status == "completed" for e in monitor_events)
