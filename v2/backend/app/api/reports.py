"""Report API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.models import Investigation, InvestigationReport
from app.db.session import get_db
from app.schemas.reports import ReportOut
from app.services.report_builder import build_report_out

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: UUID, db: Session = Depends(get_db)) -> ReportOut:
    report = (
        db.query(InvestigationReport)
        .options(joinedload(InvestigationReport.investigation))
        .filter(InvestigationReport.id == report_id)
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return build_report_out(report.investigation, report)
