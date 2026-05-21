"""Investigation API routes."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.models import Investigation
from app.db.session import SessionLocal, get_db
from app.schemas.evaluation import InvestigationEvaluationOut
from app.schemas.replay import InvestigationReplayOut
from app.schemas.investigations import (
    CreateInvestigationRequest,
    DashboardKpis,
    DashboardOut,
    InvestigationDetailOut,
    InvestigationListItem,
    RiskAlertItem,
)
from app.services.evaluation_service import run_investigation_evaluation
from app.services.replay_service import build_investigation_replay
from app.services.investigation_service import (
    create_investigation_record,
    run_investigation_workflow,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/investigations", tags=["investigations"])

_executor = ThreadPoolExecutor(max_workers=2)


def _to_list_item(inv: Investigation) -> InvestigationListItem:
    report_id = inv.report.id if inv.report else None
    return InvestigationListItem(
        id=inv.id,
        goal=inv.goal,
        metric_name=inv.metric_name,
        workflow_id=inv.workflow_id,
        status=inv.status,
        needs_investigation=inv.needs_investigation,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        report_id=report_id,
    )


def _run_workflow_bg(investigation_id: UUID) -> None:
    db = SessionLocal()
    try:
        run_investigation_workflow(db, investigation_id)
    finally:
        db.close()


@router.get("", response_model=list[InvestigationListItem])
def list_investigations(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[InvestigationListItem]:
    rows = (
        db.query(Investigation)
        .options(joinedload(Investigation.report))
        .order_by(Investigation.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_to_list_item(r) for r in rows]


@router.post("", response_model=InvestigationDetailOut, status_code=201)
def create_investigation(
    body: CreateInvestigationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> InvestigationDetailOut:
    inv = create_investigation_record(
        db,
        goal=body.goal,
        metric_name=body.metric_name,
        analysis_date=body.analysis_date,
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
    exec_sum = None
    skills = None
    if inv.report and inv.report.report_json:
        exec_sum = inv.report.report_json.get("executive_summary")
        raw = inv.report.report_json.get("executed_skills")
        if isinstance(raw, list):
            skills = raw
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
        executive_summary=exec_sum,
        executed_skills=skills,
    )


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    total = db.query(Investigation).count()
    running = db.query(Investigation).filter(Investigation.status == "running").count()
    completed = db.query(Investigation).filter(Investigation.status == "completed").count()
    failed = db.query(Investigation).filter(Investigation.status == "failed").count()

    latest = (
        db.query(Investigation)
        .options(
            joinedload(Investigation.report),
            joinedload(Investigation.steps),
        )
        .order_by(Investigation.created_at.desc())
        .limit(8)
        .all()
    )
    with_reports = [i for i in latest if i.report is not None][:5]

    alerts: list[RiskAlertItem] = []
    for inv in latest:
        monitor_step = next(
            (s for s in inv.steps if s.step_name in ("monitor", "metric_monitor")),
            None,
        )
        if monitor_step and monitor_step.output_json:
            mj = monitor_step.output_json
            if mj.get("needs_investigation"):
                alerts.append(
                    RiskAlertItem(
                        id=str(inv.id),
                        metric_name=inv.metric_name,
                        summary=monitor_step.output_preview or mj.get("summary", ""),
                        severity=str(mj.get("severity", "medium")),
                        created_at=inv.created_at,
                    )
                )

    return DashboardOut(
        kpis=DashboardKpis(
            total_investigations=total,
            running_investigations=running,
            completed_investigations=completed,
            failed_investigations=failed,
        ),
        latest_investigations=[_to_list_item(i) for i in latest[:5]],
        latest_risk_alerts=alerts[:5],
        latest_reports=[_to_list_item(i) for i in with_reports],
    )


@router.get("/{investigation_id}/replay", response_model=InvestigationReplayOut)
def get_investigation_replay(
    investigation_id: UUID,
    db: Session = Depends(get_db),
) -> InvestigationReplayOut:
    inv = (
        db.query(Investigation)
        .options(joinedload(Investigation.report))
        .filter(Investigation.id == investigation_id)
        .first()
    )
    if inv is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if inv.report is None or not inv.report.report_json:
        raise HTTPException(
            status_code=404,
            detail="Investigation report not available for replay",
        )
    try:
        return build_investigation_replay(inv)
    except Exception as exc:
        logger.error("replay build failed id=%s", investigation_id, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{investigation_id}/evaluation", response_model=InvestigationEvaluationOut)
def get_investigation_evaluation(
    investigation_id: UUID,
    db: Session = Depends(get_db),
) -> InvestigationEvaluationOut:
    inv = (
        db.query(Investigation)
        .options(joinedload(Investigation.report))
        .filter(Investigation.id == investigation_id)
        .first()
    )
    if inv is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if inv.report is None or not inv.report.report_json:
        raise HTTPException(
            status_code=404,
            detail="Investigation report not available for evaluation",
        )
    try:
        return run_investigation_evaluation(inv.id, inv.report.report_json)
    except Exception as exc:
        logger.error("evaluation failed id=%s", investigation_id, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    exec_sum = None
    skills = None
    if inv.report and inv.report.report_json:
        exec_sum = inv.report.report_json.get("executive_summary")
        raw = inv.report.report_json.get("executed_skills")
        if isinstance(raw, list):
            skills = raw
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
        executive_summary=exec_sum,
        executed_skills=skills,
    )
