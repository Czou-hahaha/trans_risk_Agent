"""Tests for investigation replay builder."""

from __future__ import annotations

from datetime import date

from replay import ReplayBuilder
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
from models.investigation_timeline import InvestigationTimelineEvent


def _full_result() -> InvestigationResult:
    monitor = _monitor()
    trend = _trend()
    contrib = _contributor()
    segments = _segments()
    strategy = _strategy()
    conclusion = _conclusion()
    ts = _ts()
    return InvestigationResult(
        investigation_id="inv-replay-1",
        workflow_id="wf-replay-1",
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
                timestamp=ts,
                duration_ms=120,
            ),
            InvestigationTimelineEvent(
                skill_name="trend_analysis",
                step_order=2,
                execution_status="completed",
                summary="trend done",
                timestamp=ts,
                duration_ms=80,
            ),
        ],
        findings=[],
        executive_summary="Portfolio FPD7 deteriorated; channel partner_X primary driver.",
        monitor_finding=monitor,
        trend_result=trend,
        contribution_findings=[contrib],
        segment_stability_result=segments,
        strategy_impact_result=strategy,
        investigation_conclusion=conclusion,
        generated_at=ts,
    )


def test_replay_builds_ordered_events() -> None:
    session = ReplayBuilder().build_from_result(_full_result(), goal="Analyze FPD7")
    assert session.total_events == len(session.events)
    assert session.events[0].event_kind == "workflow_started"
    assert session.events[-1].event_kind in ("report_generated", "workflow_completed")
    indices = [e.sequence_index for e in session.events]
    assert indices == list(range(len(session.events)))


def test_replay_includes_skill_and_finding_events() -> None:
    session = ReplayBuilder().build_from_result(_full_result())
    kinds = {e.event_kind for e in session.events}
    assert "skill_completed" in kinds or "skill_started" in kinds
    assert "finding_discovered" in kinds
    assert "report_generated" in kinds


def test_replay_timestamps_monotonic() -> None:
    session = ReplayBuilder().build_from_result(_full_result())
    stamps = [e.timestamp for e in session.events]
    assert stamps == sorted(stamps)


def test_replay_from_payload_roundtrip() -> None:
    result = _full_result()
    payload = result.model_dump(mode="json")
    session = ReplayBuilder().build_from_payload(payload, goal="test goal")
    assert session.investigation_id == result.investigation_id
    assert session.metric_name == "fpd7"
    assert any(e.event_kind == "finding_discovered" for e in session.events)


def test_replay_synthesizes_timeline_when_missing() -> None:
    result = _full_result()
    result.timeline = []
    session = ReplayBuilder().build_from_result(result)
    skill_events = [e for e in session.events if e.category == "skill"]
    assert len(skill_events) >= len(result.executed_skills)
