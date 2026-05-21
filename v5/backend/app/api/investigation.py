"""V4 investigation workspace API (alias routes)."""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.investigations import _run_workflow_bg, _to_list_item
from app.db.models import Investigation, InvestigationReport
from app.db.session import get_db
from app.schemas.investigations import (
    CreateInvestigationRequest,
    InvestigationDetailOut,
    RunInvestigationRequest,
)
from app.services.investigation_service import create_investigation_record
from app.services.report_builder import build_report_out

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/investigation", tags=["investigation-workspace"])


def _detail(inv: Investigation) -> InvestigationDetailOut:
    return InvestigationDetailOut(
        id=inv.id,
        goal=inv.goal,
        metric_name=inv.metric_name,
        analysis_date=inv.analysis_date,
        workflow_id=inv.workflow_id,
        status=inv.status,
        needs_investigation=inv.needs_investigation,
        error_message=inv.error_message,
        failed_stage=inv.failed_stage,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        steps=inv.steps,
        report_id=inv.report.id if inv.report else None,
        executive_summary=_executive_summary(inv),
        executed_skills=_executed_skills(inv),
    )


def _executive_summary(inv: Investigation) -> str | None:
    if inv.report and inv.report.report_json:
        return inv.report.report_json.get("executive_summary")
    return None


def _executed_skills(inv: Investigation) -> list[str] | None:
    if inv.report and inv.report.report_json:
        skills = inv.report.report_json.get("executed_skills")
        if isinstance(skills, list):
            return skills
    return None


@router.post("/run", response_model=InvestigationDetailOut, status_code=201)
def run_investigation(
    body: RunInvestigationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> InvestigationDetailOut:
    goal = body.goal or f"Investigate {body.metric_name} on {body.analysis_date}"
    analysis = (
        date.fromisoformat(body.analysis_date)
        if isinstance(body.analysis_date, str)
        else body.analysis_date
    )
    inv = create_investigation_record(
        db,
        goal=goal,
        metric_name=body.metric_name,
        analysis_date=analysis,
    )
    background_tasks.add_task(_run_workflow_bg, inv.id)
    db.refresh(inv)
    inv = (
        db.query(Investigation)
        .options(joinedload(Investigation.steps), joinedload(Investigation.report))
        .filter(Investigation.id == inv.id)
        .first()
    )
    assert inv is not None
    return _detail(inv)


@router.get("/{investigation_id}", response_model=InvestigationDetailOut)
def get_investigation(
    investigation_id: UUID,
    db: Session = Depends(get_db),
) -> InvestigationDetailOut:
    inv = (
        db.query(Investigation)
        .options(joinedload(Investigation.steps), joinedload(Investigation.report))
        .filter(Investigation.id == investigation_id)
        .first()
    )
    if inv is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return _detail(inv)


@router.get("/{investigation_id}/report")
def get_investigation_report(
    investigation_id: UUID,
    db: Session = Depends(get_db),
):
    inv = (
        db.query(Investigation)
        .options(joinedload(Investigation.report))
        .filter(Investigation.id == investigation_id)
        .first()
    )
    if inv is None or inv.report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return build_report_out(inv, inv.report)
