"""Repository for investigation_snapshots table."""

from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from intelligence_memory.schemas.investigation_snapshot import InvestigationSnapshot
from intelligence_memory.storage.persistence_models import InvestigationSnapshotRow

logger = logging.getLogger(__name__)


class InvestigationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_snapshot(self, snapshot: InvestigationSnapshot) -> InvestigationSnapshot:
        row = InvestigationSnapshotRow(
            investigation_id=snapshot.investigation_id,
            metric_name=snapshot.metric_name,
            analysis_date=snapshot.analysis_date,
            workflow_status=snapshot.workflow_status,
            findings_count=snapshot.findings_count,
            needs_investigation=snapshot.needs_investigation,
            trigger_reason=snapshot.trigger_reason,
            generated_at=snapshot.generated_at,
        )
        self._session.merge(row)
        self._session.flush()
        return snapshot

    def get_snapshot(self, investigation_id: str) -> InvestigationSnapshot | None:
        row = self._session.get(InvestigationSnapshotRow, investigation_id)
        if row is None:
            return None
        return InvestigationSnapshot(
            investigation_id=row.investigation_id,
            metric_name=row.metric_name,
            analysis_date=row.analysis_date,
            workflow_status=row.workflow_status,
            findings_count=row.findings_count,
            needs_investigation=row.needs_investigation,
            trigger_reason=row.trigger_reason,
            generated_at=row.generated_at,
        )

    def list_by_metric(self, metric_name: str, *, limit: int = 50) -> list[InvestigationSnapshot]:
        rows = (
            self._session.query(InvestigationSnapshotRow)
            .filter(InvestigationSnapshotRow.metric_name == metric_name)
            .order_by(InvestigationSnapshotRow.generated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            InvestigationSnapshot(
                investigation_id=r.investigation_id,
                metric_name=r.metric_name,
                analysis_date=r.analysis_date,
                workflow_status=r.workflow_status,
                findings_count=r.findings_count,
                needs_investigation=r.needs_investigation,
                trigger_reason=r.trigger_reason,
                generated_at=r.generated_at,
            )
            for r in rows
        ]

    def list_recent(
        self,
        *,
        limit: int = 20,
        metric_name: str | None = None,
    ) -> list[InvestigationSnapshot]:
        query = self._session.query(InvestigationSnapshotRow)
        if metric_name is not None:
            query = query.filter(InvestigationSnapshotRow.metric_name == metric_name)
        rows = (
            query.order_by(InvestigationSnapshotRow.generated_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_snapshot(r) for r in rows]

    def list_in_date_range(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        *,
        metric_name: str | None = None,
        limit: int = 200,
    ) -> list[InvestigationSnapshot]:
        query = self._session.query(InvestigationSnapshotRow)
        if metric_name is not None:
            query = query.filter(InvestigationSnapshotRow.metric_name == metric_name)
        if date_from is not None:
            query = query.filter(InvestigationSnapshotRow.analysis_date >= date_from)
        if date_to is not None:
            query = query.filter(InvestigationSnapshotRow.analysis_date <= date_to)
        rows = (
            query.order_by(InvestigationSnapshotRow.generated_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_snapshot(r) for r in rows]

    def list_all(self, *, limit: int = 500) -> list[InvestigationSnapshot]:
        rows = (
            self._session.query(InvestigationSnapshotRow)
            .order_by(InvestigationSnapshotRow.generated_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_snapshot(r) for r in rows]


def _row_to_snapshot(row: InvestigationSnapshotRow) -> InvestigationSnapshot:
    return InvestigationSnapshot(
        investigation_id=row.investigation_id,
        metric_name=row.metric_name,
        analysis_date=row.analysis_date,
        workflow_status=row.workflow_status,
        findings_count=row.findings_count,
        needs_investigation=row.needs_investigation,
        trigger_reason=row.trigger_reason,
        generated_at=row.generated_at,
    )
