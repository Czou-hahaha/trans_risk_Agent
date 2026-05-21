"""Build ordered replay timelines from persisted investigation results."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from models.investigation_timeline import InvestigationTimelineEvent
from replay.schemas.replay_timeline_event import (
    InvestigationReplay,
    ReplayTimelineEvent,
)
from workflow.result import InvestigationResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_event_id() -> str:
    return str(uuid4())


def _kind_for_status(status: str) -> str:
    if status == "completed":
        return "skill_completed"
    if status == "skipped":
        return "skill_skipped"
    if status == "failed":
        return "skill_failed"
    return "skill_started"


class ReplayBuilder:
    """Transform InvestigationResult into a timestamp-ordered replay session."""

    def build_from_result(
        self,
        result: InvestigationResult,
        *,
        goal: str = "",
    ) -> InvestigationReplay:
        events: list[ReplayTimelineEvent] = []
        base_ts = result.generated_at or _utcnow()

        events.append(
            ReplayTimelineEvent(
                event_id=_new_event_id(),
                sequence_index=0,
                timestamp=base_ts - timedelta(seconds=30),
                event_kind="workflow_started",
                category="workflow",
                title="Investigation started",
                summary=(
                    f"Metric {result.metric_name} · "
                    f"analysis date {result.analysis_date}"
                ),
                payload={
                    "metric_name": result.metric_name,
                    "analysis_date": str(result.analysis_date),
                    "trigger_reason": result.trigger_reason,
                    "needs_investigation": result.needs_investigation,
                },
            )
        )

        timeline = sorted(
            list(result.timeline),
            key=lambda e: (e.step_order, e.timestamp),
        )
        if not timeline:
            timeline = self._timeline_from_executed_skills(result, base_ts)

        seq = 1
        for tl_event in timeline:
            seq = self._append_skill_events(events, tl_event, seq)

        seq = self._append_finding_events(events, result, seq, base_ts)
        seq = self._append_completion_events(events, result, seq, base_ts)

        _category_order = {"workflow": 0, "skill": 1, "finding": 2, "report": 3}
        events.sort(
            key=lambda e: (
                e.timestamp,
                _category_order.get(e.category, 9),
                e.sequence_index,
            )
        )
        for i, ev in enumerate(events):
            ev.sequence_index = i

        return InvestigationReplay(
            investigation_id=result.investigation_id,
            workflow_id=result.workflow_id,
            metric_name=result.metric_name,
            goal=goal,
            workflow_status=result.workflow_status,
            total_events=len(events),
            events=events,
            executed_skills=list(result.executed_skills),
            generated_at=result.generated_at,
        )

    def build_from_payload(
        self,
        payload: dict[str, Any],
        *,
        goal: str = "",
    ) -> InvestigationReplay:
        """Build replay from serialized report_json."""
        result = InvestigationResult.model_validate(payload)
        return self.build_from_result(result, goal=goal)

    def _timeline_from_executed_skills(
        self,
        result: InvestigationResult,
        base_ts: datetime,
    ) -> list[InvestigationTimelineEvent]:
        """Synthesize timeline when engine events were not persisted."""
        order_map = {
            "metric_monitor": 1,
            "trend_analysis": 2,
            "dimension_contribution": 3,
            "segment_stability": 4,
            "strategy_impact": 5,
            "finding_summary": 6,
            "report_builder": 7,
        }
        events: list[InvestigationTimelineEvent] = []
        offset = 0
        for skill in sorted(result.executed_skills, key=lambda s: order_map.get(s, 99)):
            ts = base_ts - timedelta(seconds=60 - offset)
            offset += 5
            events.append(
                InvestigationTimelineEvent(
                    timestamp=ts,
                    skill_name=skill,  # type: ignore[arg-type]
                    execution_status="completed",
                    summary=f"{skill} completed",
                    step_order=order_map.get(skill, offset),
                )
            )
        return events

    def _append_skill_events(
        self,
        events: list[ReplayTimelineEvent],
        tl_event: InvestigationTimelineEvent,
        seq: int,
    ) -> int:
        status = tl_event.execution_status
        skill = tl_event.skill_name

        if status == "running":
            events.append(
                ReplayTimelineEvent(
                    event_id=_new_event_id(),
                    sequence_index=seq,
                    timestamp=tl_event.timestamp,
                    event_kind="skill_started",
                    category="skill",
                    skill_name=skill,
                    execution_status=status,
                    title=f"{skill} started",
                    summary=tl_event.summary or "Skill execution started",
                    payload={"step_order": tl_event.step_order},
                )
            )
            return seq + 1

        kind = _kind_for_status(status)
        events.append(
            ReplayTimelineEvent(
                event_id=_new_event_id(),
                sequence_index=seq,
                timestamp=tl_event.timestamp,
                event_kind=kind,  # type: ignore[arg-type]
                category="skill",
                skill_name=skill,
                execution_status=status,
                title=f"{skill} {status}",
                summary=tl_event.summary,
                duration_ms=tl_event.duration_ms,
                payload={"step_order": tl_event.step_order},
            )
        )
        return seq + 1

    def _append_finding_events(
        self,
        events: list[ReplayTimelineEvent],
        result: InvestigationResult,
        seq: int,
        base_ts: datetime,
    ) -> int:
        """Emit finding_discovered events aligned to skills that produced them."""
        skill_findings: list[tuple[str, dict[str, Any]]] = []

        if result.monitor_finding:
            skill_findings.append(
                ("metric_monitor", result.monitor_finding.model_dump(mode="json"))
            )
        if result.trend_result:
            skill_findings.append(
                (
                    "trend_analysis",
                    result.trend_result.trend_finding.model_dump(mode="json"),
                )
            )
        for c in result.contribution_findings:
            skill_findings.append(
                ("dimension_contribution", c.model_dump(mode="json"))
            )
        if result.segment_stability_result:
            for seg in result.segment_stability_result.top_unstable_segments[:3]:
                skill_findings.append(
                    ("segment_stability", seg.model_dump(mode="json"))
                )
        if result.strategy_impact_result:
            for f in result.strategy_impact_result.findings[:3]:
                skill_findings.append(("strategy_impact", f.model_dump(mode="json")))
        if result.investigation_conclusion:
            skill_findings.append(
                (
                    "finding_summary",
                    result.investigation_conclusion.model_dump(mode="json"),
                )
            )

        if not skill_findings and result.findings:
            for i, raw in enumerate(result.findings):
                ftype = str(raw.get("finding_type", raw.get("metric_name", "finding")))
                skill_findings.append((ftype, raw))

        skill_ts: dict[str, datetime] = {}
        for ev in events:
            if ev.skill_name and ev.event_kind in (
                "skill_completed",
                "skill_skipped",
                "skill_failed",
            ):
                skill_ts[ev.skill_name] = ev.timestamp

        offset_ms = 0
        for skill, finding in skill_findings:
            ts = skill_ts.get(skill, base_ts) + timedelta(milliseconds=50 + offset_ms)
            offset_ms += 10
            summary = str(
                finding.get("summary")
                or finding.get("business_summary")
                or finding.get("risk_hypothesis")
                or f"Finding from {skill}"
            )[:400]
            events.append(
                ReplayTimelineEvent(
                    event_id=_new_event_id(),
                    sequence_index=seq,
                    timestamp=ts,
                    event_kind="finding_discovered",
                    category="finding",
                    skill_name=skill,
                    title=f"Finding: {skill}",
                    summary=summary,
                    payload={"finding": finding, "finding_type": finding.get("finding_type")},
                )
            )
            seq += 1
        return seq

    def _append_completion_events(
        self,
        events: list[ReplayTimelineEvent],
        result: InvestigationResult,
        seq: int,
        base_ts: datetime,
    ) -> int:
        end_ts = result.generated_at or base_ts
        events.append(
            ReplayTimelineEvent(
                event_id=_new_event_id(),
                sequence_index=seq,
                timestamp=end_ts,
                event_kind="workflow_completed",
                category="workflow",
                title="Workflow completed",
                summary=f"Status: {result.workflow_status}",
                payload={
                    "workflow_status": result.workflow_status,
                    "needs_investigation": result.needs_investigation,
                    "executed_skills": result.executed_skills,
                },
            )
        )
        seq += 1

        if result.executive_summary or result.generated_report_path:
            events.append(
                ReplayTimelineEvent(
                    event_id=_new_event_id(),
                    sequence_index=seq,
                    timestamp=end_ts + timedelta(milliseconds=100),
                    event_kind="report_generated",
                    category="report",
                    skill_name="report_builder",
                    title="Investigation report generated",
                    summary=(result.executive_summary or "Report ready")[:500],
                    payload={
                        "executive_summary": result.executive_summary,
                        "generated_report_path": result.generated_report_path,
                        "finding_count": len(result.findings),
                    },
                )
            )
            seq += 1
        return seq
