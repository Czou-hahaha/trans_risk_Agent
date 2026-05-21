"""Tests for deterministic investigation evaluation layer."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from evaluation import EvaluationService
from evaluation.evaluators import (
    FindingEvaluator,
    PatternEvaluator,
    ReportEvaluator,
    WorkflowEvaluator,
)
from evaluation.schemas.evaluation_result import EvaluationResult
from intelligence_memory.patterns.schemas.detected_pattern import DetectedPattern
from models.investigation_timeline import InvestigationTimelineEvent
from workflow.result import InvestigationResult
from tests.test_investigation_workflow import (
    _conclusion,
    _contributor,
    _monitor,
    _segments,
    _strategy,
    _trend,
    _ts,
)


def _finding_dict(**overrides: object) -> dict:
    base = {
        "finding_id": "f-1",
        "finding_type": "dimension_contribution",
        "metric_name": "fpd7",
        "summary": "channel=partner_X drove deterioration",
        "evidence": {"dimension": "channel", "sample_size": 1000},
        "generated_at": _ts().isoformat(),
        "dimension_name": "channel",
        "dimension_value": "partner_X",
        "contribution_pp": 0.55,
        "delta_pp": 1.3,
    }
    base.update(overrides)
    return base


def _full_result() -> InvestigationResult:
    monitor = _monitor()
    trend = _trend()
    contrib = _contributor()
    segments = _segments()
    strategy = _strategy()
    conclusion = _conclusion()
    return InvestigationResult(
        investigation_id="inv-eval-1",
        workflow_id="inv-eval-1",
        metric_name="fpd7",
        analysis_date=date(2026, 5, 20),
        workflow_status="completed",
        needs_investigation=True,
        trigger_reason="metric_anomaly",
        executed_skills=[
            "metric_monitor",
            "trend_analysis",
            "dimension_contribution",
            "segment_stability",
            "strategy_impact",
            "finding_summary",
            "report_builder",
        ],
        timeline=[
            InvestigationTimelineEvent(
                skill_name="metric_monitor",
                step_order=1,
                execution_status="completed",
                summary="monitor done",
                timestamp=_ts(),
            ),
        ],
        findings=[
            {**monitor.model_dump(mode="json"), "evidence": {"period": "current_vs_previous"}},
            {
                **trend.trend_finding.model_dump(mode="json"),
                "evidence": {"window_days": 60},
            },
            contrib.model_dump(mode="json"),
            {
                **segments.top_unstable_segments[0].model_dump(mode="json"),
                "evidence": {"stability_score": 0.3},
            },
            {
                **strategy.findings[0].model_dump(mode="json"),
                "evidence": {"metric_deltas": {"fpd7": {"delta_pp": -1.1}}},
            },
        ],
        executive_summary=(
            "Portfolio FPD7 showed 2.30pp deterioration. "
            "Driven by channel=partner_X. Trend upward. Strategy RISK_003 effective."
        ),
        generated_report_path="/tmp/report.md",
        monitor_finding=monitor,
        trend_result=trend,
        contribution_findings=[contrib],
        segment_stability_result=segments,
        strategy_impact_result=strategy,
        investigation_conclusion=conclusion,
        generated_at=_ts(),
    )


class TestFindingEvaluator:
    def test_high_score_for_complete_findings(self) -> None:
        findings = [_finding_dict(), _finding_dict(finding_id="f-2", dimension_value="paid")]
        result = FindingEvaluator().evaluate(findings)
        assert result.evaluation_type == "finding_quality"
        assert result.evaluation_score >= 0.85
        assert not result.detected_issues

    def test_detects_duplicate_and_missing_evidence(self) -> None:
        findings = [
            _finding_dict(finding_id="f-a"),
            _finding_dict(finding_id="f-b"),
            {
                "finding_id": "f-c",
                "finding_type": "trend_analysis",
                "metric_name": "fpd7",
                "summary": "x",
                "evidence": {},
                "generated_at": _ts().isoformat(),
            },
        ]
        result = FindingEvaluator().evaluate(findings)
        assert result.evaluation_score < 0.85
        assert any("duplicate_finding" in i for i in result.detected_issues)
        assert any("missing_evidence" in i for i in result.detected_issues)


class TestWorkflowEvaluator:
    def test_full_pipeline_high_score(self) -> None:
        result = WorkflowEvaluator().evaluate(_full_result())
        assert result.evaluation_type == "workflow_consistency"
        assert result.evaluation_score >= 0.7

    def test_missing_skills_lower_score(self) -> None:
        broken = _full_result()
        broken.executed_skills = ["metric_monitor"]
        result = WorkflowEvaluator().evaluate(broken)
        assert result.evaluation_score < 0.7
        assert any("missing" in i or "planned" in i for i in result.detected_issues)


class TestReportEvaluator:
    def test_complete_report_high_score(self) -> None:
        result = ReportEvaluator().evaluate(_full_result())
        assert result.evaluation_type == "report_completeness"
        assert result.evaluation_score >= 0.75

    def test_missing_executive_summary(self) -> None:
        broken = _full_result()
        broken.executive_summary = ""
        result = ReportEvaluator().evaluate(broken)
        assert any("executive_summary" in i for i in result.detected_issues)


class TestPatternEvaluator:
    def test_scores_linked_patterns(self) -> None:
        patterns = [
            DetectedPattern(
                pattern_id="recurring_contributor:channel:partner_X:fpd7",
                pattern_type="recurring_contributor",
                pattern_summary="partner_X top contributor 3x",
                supporting_findings=["f1", "f2", "f3"],
                confidence_score=0.82,
                first_detected_at=_ts(),
                last_detected_at=_ts(),
                investigation_ids=["inv-eval-1", "inv-2", "inv-3"],
                occurrence_count=3,
            )
        ]
        result = PatternEvaluator().evaluate(patterns, investigation_id="inv-eval-1")
        assert result.evaluation_score >= 0.5

    def test_flags_low_confidence_pattern(self) -> None:
        patterns = [
            DetectedPattern(
                pattern_id="p-weak",
                pattern_type="strategy_side_effect",
                pattern_summary="weak",
                confidence_score=0.2,
                first_detected_at=_ts(),
                last_detected_at=_ts(),
                investigation_ids=["inv-eval-1"],
                occurrence_count=1,
            )
        ]
        result = PatternEvaluator().evaluate(patterns, investigation_id="inv-eval-1")
        assert any("low_pattern_confidence" in i for i in result.detected_issues)


class TestEvaluationService:
    def test_bundle_aggregates_four_dimensions(self) -> None:
        svc = EvaluationService()
        bundle = svc.evaluate_investigation(
            _full_result(),
            include_patterns=False,
        )
        assert bundle.investigation_id == "inv-eval-1"
        assert len(bundle.results) == 3
        assert 0.0 <= bundle.metrics.overall_score <= 1.0
        assert bundle.metrics.workflow_quality == bundle.results[1].evaluation_score

    def test_evaluate_from_payload(self) -> None:
        payload = _full_result().model_dump(mode="json")
        bundle = EvaluationService().evaluate_from_payload(
            payload,
            include_patterns=False,
        )
        assert bundle.metrics.finding_confidence > 0.5
