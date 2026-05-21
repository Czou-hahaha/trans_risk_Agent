"""Repository for stored_findings table."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from intelligence_memory.schemas.stored_finding import StoredFinding
from intelligence_memory.storage.persistence_models import StoredFindingRow

logger = logging.getLogger(__name__)


class FindingSearchFilters:
    """Optional filters for cross-investigation finding queries."""

    __slots__ = (
        "metric_name",
        "dimension_name",
        "dimension_value",
        "finding_type",
        "date_from",
        "date_to",
        "limit",
    )

    def __init__(
        self,
        *,
        metric_name: str | None = None,
        dimension_name: str | None = None,
        dimension_value: str | None = None,
        finding_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 500,
    ) -> None:
        self.metric_name = metric_name
        self.dimension_name = dimension_name
        self.dimension_value = dimension_value
        self.finding_type = finding_type
        self.date_from = date_from
        self.date_to = date_to
        self.limit = limit


class FindingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(self, finding: StoredFinding) -> StoredFinding:
        row = StoredFindingRow(
            finding_id=finding.finding_id,
            investigation_id=finding.investigation_id,
            metric_name=finding.metric_name,
            finding_type=finding.finding_type,
            dimension_name=finding.dimension_name,
            dimension_value=finding.dimension_value,
            summary=finding.summary,
            severity=finding.severity,
            contribution_pp=finding.contribution_pp,
            delta_pp=finding.delta_pp,
            approval_delta_pp=finding.approval_delta_pp,
            volume_delta_pct=finding.volume_delta_pct,
            generated_at=finding.generated_at,
        )
        self._session.merge(row)
        self._session.flush()
        return finding

    def insert_batch(self, findings: list[StoredFinding]) -> list[StoredFinding]:
        for finding in findings:
            self.insert(finding)
        return findings

    def list_by_metric(self, metric_name: str, *, limit: int = 100) -> list[StoredFinding]:
        rows = (
            self._session.query(StoredFindingRow)
            .filter(StoredFindingRow.metric_name == metric_name)
            .order_by(StoredFindingRow.generated_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_schema(r) for r in rows]

    def list_by_dimension(
        self,
        dimension_name: str,
        dimension_value: str,
        *,
        limit: int = 100,
    ) -> list[StoredFinding]:
        rows = (
            self._session.query(StoredFindingRow)
            .filter(
                StoredFindingRow.dimension_name == dimension_name,
                StoredFindingRow.dimension_value == dimension_value,
            )
            .order_by(StoredFindingRow.generated_at.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_schema(r) for r in rows]

    def list_by_investigation(self, investigation_id: str) -> list[StoredFinding]:
        rows = (
            self._session.query(StoredFindingRow)
            .filter(StoredFindingRow.investigation_id == investigation_id)
            .order_by(StoredFindingRow.generated_at.asc())
            .all()
        )
        return [_row_to_schema(r) for r in rows]

    def search(self, filters: FindingSearchFilters) -> list[StoredFinding]:
        query = self._session.query(StoredFindingRow)
        if filters.metric_name is not None:
            query = query.filter(StoredFindingRow.metric_name == filters.metric_name)
        if filters.dimension_name is not None:
            query = query.filter(StoredFindingRow.dimension_name == filters.dimension_name)
        if filters.dimension_value is not None:
            query = query.filter(StoredFindingRow.dimension_value == filters.dimension_value)
        if filters.finding_type is not None:
            query = query.filter(StoredFindingRow.finding_type == filters.finding_type)
        if filters.date_from is not None:
            query = query.filter(StoredFindingRow.generated_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.filter(StoredFindingRow.generated_at <= filters.date_to)
        rows = (
            query.order_by(StoredFindingRow.generated_at.desc())
            .limit(filters.limit)
            .all()
        )
        return [_row_to_schema(r) for r in rows]


def _row_to_schema(row: StoredFindingRow) -> StoredFinding:
    return StoredFinding(
        finding_id=row.finding_id,
        investigation_id=row.investigation_id,
        metric_name=row.metric_name,
        finding_type=row.finding_type,
        dimension_name=row.dimension_name,
        dimension_value=row.dimension_value,
        summary=row.summary,
        severity=row.severity,
        contribution_pp=row.contribution_pp,
        delta_pp=row.delta_pp,
        approval_delta_pp=row.approval_delta_pp,
        volume_delta_pct=row.volume_delta_pct,
        generated_at=row.generated_at,
    )
