"""Persisted V4 investigation workflow orchestration."""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Investigation, InvestigationReport, InvestigationStep
from app.services.goal_parser import parse_metric_from_goal
from app.services.preview import (
    contribution_preview,
    monitor_preview,
    segment_preview,
    strategy_preview,
    summary_preview,
    trend_preview,
)

logger = logging.getLogger(__name__)

_ENGINE = settings.engine_root
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from dotenv import load_dotenv

load_dotenv(_ENGINE.parent / ".env")

from workflow.investigation_workflow import InvestigationWorkflow  # noqa: E402
from workflow.result import InvestigationResult  # noqa: E402

STEP_DEFS: list[tuple[str, int]] = [
    ("metric_monitor", 1),
    ("trend_analysis", 2),
    ("dimension_contribution", 3),
    ("segment_stability", 4),
    ("strategy_impact", 5),
    ("finding_summary", 6),
    ("report_builder", 7),
]

# Legacy step_name aliases for UI
STEP_ALIASES: dict[str, str] = {
    "monitor": "metric_monitor",
    "contribution": "dimension_contribution",
    "summary": "finding_summary",
    "report": "report_builder",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_investigation_record(
    db: Session,
    *,
    goal: str,
    metric_name: Optional[str] = None,
    analysis_date: Optional[date] = None,
) -> Investigation:
    metric = metric_name or parse_metric_from_goal(goal)
    workflow_id = str(uuid4())
    inv = Investigation(
        goal=goal,
        metric_name=metric,
        workflow_id=workflow_id,
        status="running",
        analysis_date=analysis_date,
    )
    db.add(inv)
    db.flush()

    for step_name, order in STEP_DEFS:
        db.add(
            InvestigationStep(
                investigation_id=inv.id,
                step_name=step_name,
                step_order=order,
                status="pending",
            )
        )
    db.commit()
    db.refresh(inv)
    return inv


def _get_step(db: Session, inv_id: UUID, step_name: str) -> InvestigationStep:
    step = (
        db.query(InvestigationStep)
        .filter(
            InvestigationStep.investigation_id == inv_id,
            InvestigationStep.step_name == step_name,
        )
        .first()
    )
    if step is None:
        raise ValueError(f"step not found: {step_name}")
    return step


def _sync_steps_from_timeline(db: Session, inv: Investigation, result: InvestigationResult) -> None:
    """Map engine timeline events onto persisted investigation steps."""
    by_skill = {s.step_name: s for s in inv.steps}
    for event in sorted(result.timeline, key=lambda e: e.step_order):
        step = by_skill.get(event.skill_name)
        if step is None:
            continue
        step.status = event.execution_status
        step.output_preview = (event.summary or "")[:500]
        if event.execution_status == "running":
            step.started_at = event.timestamp
        if event.execution_status in ("completed", "skipped", "failed"):
            step.completed_at = event.timestamp


def _preview_for_step(step_name: str, result: InvestigationResult) -> str:
    if step_name == "metric_monitor" and result.monitor_finding:
        return monitor_preview(result.monitor_finding)
    if step_name == "trend_analysis" and result.trend_result:
        return trend_preview(result.trend_result.trend_finding)
    if step_name == "dimension_contribution":
        return contribution_preview(result.contribution_findings)
    if step_name == "segment_stability" and result.segment_stability_result:
        return segment_preview(result.segment_stability_result.top_unstable_segments)
    if step_name == "strategy_impact" and result.strategy_impact_result:
        f = result.strategy_impact_result.findings
        return strategy_preview(f[0]) if f else "—"
    if step_name == "finding_summary" and result.investigation_conclusion:
        return summary_preview(result.investigation_conclusion)
    if step_name == "report_builder":
        return result.executive_summary[:300] if result.executive_summary else "Report ready"
    return "—"


def _output_for_step(step_name: str, result: InvestigationResult) -> dict:
    if step_name == "metric_monitor" and result.monitor_finding:
        return result.monitor_finding.model_dump(mode="json")
    if step_name == "trend_analysis" and result.trend_result:
        return result.trend_result.model_dump(mode="json")
    if step_name == "dimension_contribution":
        return {
            "top_contributors": [
                c.model_dump(mode="json") for c in result.contribution_findings
            ]
        }
    if step_name == "segment_stability" and result.segment_stability_result:
        return result.segment_stability_result.model_dump(mode="json")
    if step_name == "strategy_impact" and result.strategy_impact_result:
        return result.strategy_impact_result.model_dump(mode="json")
    if step_name == "finding_summary" and result.investigation_conclusion:
        return result.investigation_conclusion.model_dump(mode="json")
    if step_name == "report_builder":
        return {
            "executive_summary": result.executive_summary,
            "generated_report_path": result.generated_report_path,
        }
    return {}


def _persist_report(db: Session, inv: Investigation, result: InvestigationResult) -> InvestigationReport:
    report_payload = result.model_dump(mode="json")
    report = InvestigationReport(investigation_id=inv.id, report_json=report_payload)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def run_investigation_workflow(db: Session, investigation_id: UUID) -> None:
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if inv is None:
        logger.error("investigation not found id=%s", investigation_id)
        return

    analysis_date = inv.analysis_date or date(2026, 3, 7)

    try:
        result = InvestigationWorkflow(
            inv.metric_name,
            analysis_date=analysis_date,
            investigation_id=inv.workflow_id,
        ).execute()

        for step_name, _ in STEP_DEFS:
            step = _get_step(db, inv.id, step_name)
            if step_name in result.executed_skills:
                step.status = "completed"
            elif step_name in {e.skill_name for e in result.timeline if e.execution_status == "skipped"}:
                step.status = "skipped"
            else:
                step.status = "skipped"
                step.output_preview = "not required for this investigation"
            if step_name in result.executed_skills or step.status == "skipped":
                step.completed_at = _utcnow()
                step.output_preview = _preview_for_step(step_name, result)
                step.output_json = _output_for_step(step_name, result)

        _sync_steps_from_timeline(db, inv, result)

        inv.status = (
            "completed"
            if result.workflow_status in ("completed", "completed_no_issue")
            else "failed"
        )
        inv.needs_investigation = result.needs_investigation
        inv.error_message = None
        inv.failed_stage = None
        inv.updated_at = _utcnow()
        db.commit()
        _persist_report(db, inv, result)

    except Exception as exc:
        logger.error("investigation failed id=%s", investigation_id, exc_info=True)
        inv.status = "failed"
        inv.error_message = str(exc)
        inv.updated_at = _utcnow()
        db.commit()
