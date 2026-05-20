"""Persisted investigation workflow orchestration."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Investigation, InvestigationReport, InvestigationStep
from app.services.goal_parser import parse_metric_from_goal
from app.services.preview import contribution_preview, monitor_preview, summary_preview

logger = logging.getLogger(__name__)

_ENGINE = settings.engine_root
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from dotenv import load_dotenv

load_dotenv(_ENGINE.parent / ".env")

from workflow.context import WorkflowContext  # noqa: E402
from workflow.runner import InvestigationWorkflowRunner  # noqa: E402
from workflow.status import WorkflowStatus  # noqa: E402

STEP_DEFS: list[tuple[str, int]] = [
    ("monitor", 1),
    ("contribution", 2),
    ("summary", 3),
]

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_investigation_record(
    db: Session, *, goal: str, metric_name: Optional[str] = None
) -> Investigation:
    metric = metric_name or parse_metric_from_goal(goal)
    workflow_id = str(uuid4())
    inv = Investigation(
        goal=goal,
        metric_name=metric,
        workflow_id=workflow_id,
        status="running",
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


def _mark_step_running(db: Session, step: InvestigationStep) -> None:
    step.status = "running"
    step.started_at = _utcnow()
    db.commit()


def _mark_step_completed(
    db: Session,
    step: InvestigationStep,
    *,
    preview: str,
    output: dict,
) -> None:
    step.status = "completed"
    step.completed_at = _utcnow()
    step.output_preview = preview
    step.output_json = output
    db.commit()


def _mark_step_skipped(db: Session, step: InvestigationStep, preview: str) -> None:
    step.status = "skipped"
    step.completed_at = _utcnow()
    step.output_preview = preview
    db.commit()


def _persist_report(db: Session, inv: Investigation, result) -> InvestigationReport:
    conclusion = result.investigation_conclusion
    contributors = result.contribution_findings or []
    report_payload = {
        "workflow_id": result.workflow_id,
        "workflow_status": result.workflow_status,
        "needs_investigation": result.needs_investigation,
        "monitor_finding": (
            result.monitor_finding.model_dump(mode="json") if result.monitor_finding else None
        ),
        "contribution_findings": [
            c.model_dump(mode="json") for c in contributors
        ],
        "investigation_conclusion": (
            conclusion.model_dump(mode="json") if conclusion else None
        ),
        "generated_at": result.generated_at.isoformat(),
    }
    report = InvestigationReport(investigation_id=inv.id, report_json=report_payload)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def run_investigation_workflow(db: Session, investigation_id: UUID) -> None:
    """Execute V1 workflow with step-level persistence."""
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if inv is None:
        logger.error("investigation not found id=%s", investigation_id)
        return

    runner = InvestigationWorkflowRunner(
        metric_name=inv.metric_name,
        workflow_id=inv.workflow_id,
    )
    runner._context = WorkflowContext(
        workflow_id=inv.workflow_id,
        metric_name=inv.metric_name,
        current_period=runner._current_period,
        previous_period=runner._previous_period,
        started_at=_utcnow(),
        workflow_status=WorkflowStatus.RUNNING,
    )

    try:
        monitor_step = _get_step(db, inv.id, "monitor")
        _mark_step_running(db, monitor_step)

        monitor_finding = runner.run_monitor_stage()
        runner.context.monitor_finding = monitor_finding  # type: ignore[union-attr]

        _mark_step_completed(
            db,
            monitor_step,
            preview=monitor_preview(monitor_finding),
            output=monitor_finding.model_dump(mode="json"),
        )

        if not monitor_finding.needs_investigation:
            inv.status = "completed"
            inv.needs_investigation = False
            inv.updated_at = _utcnow()
            for name, _ in STEP_DEFS[1:]:
                step = _get_step(db, inv.id, name)
                _mark_step_skipped(db, step, "skipped — no investigation required")
            db.commit()

            result = runner.build_final_result()
            runner.context.workflow_status = WorkflowStatus.COMPLETED_NO_ISSUE  # type: ignore[union-attr]
            _persist_report(db, inv, result)
            return

        inv.needs_investigation = True
        db.commit()

        contrib_step = _get_step(db, inv.id, "contribution")
        _mark_step_running(db, contrib_step)
        contributors = runner.run_contribution_stage()
        runner.context.contribution_findings = contributors  # type: ignore[union-attr]
        _mark_step_completed(
            db,
            contrib_step,
            preview=contribution_preview(contributors),
            output={"top_contributors": [c.model_dump(mode="json") for c in contributors]},
        )

        summary_step = _get_step(db, inv.id, "summary")
        _mark_step_running(db, summary_step)
        conclusion = runner.run_summary_stage()
        runner.context.investigation_conclusion = conclusion  # type: ignore[union-attr]
        _mark_step_completed(
            db,
            summary_step,
            preview=summary_preview(conclusion),
            output=conclusion.model_dump(mode="json"),
        )

        runner.context.workflow_status = WorkflowStatus.COMPLETED  # type: ignore[union-attr]
        result = runner.build_final_result()
        inv.status = "completed"
        inv.updated_at = _utcnow()
        db.commit()
        _persist_report(db, inv, result)

    except Exception as exc:
        logger.error("investigation failed id=%s", investigation_id, exc_info=True)
        inv.status = "failed"
        inv.error_message = str(exc)
        inv.failed_stage = getattr(runner.context, "failed_stage", None) if runner.context else None
        inv.updated_at = _utcnow()
        db.commit()
