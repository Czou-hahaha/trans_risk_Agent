"""Deterministic historical finding lookup across investigations."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, time, timezone
from typing import NamedTuple

from sqlalchemy.orm import Session

from intelligence_memory.repositories.finding_repository import (
    FindingRepository,
    FindingSearchFilters,
)
from intelligence_memory.schemas.stored_finding import StoredFinding

logger = logging.getLogger(__name__)

DETERIORATION_FINDING_TYPES = frozenset(
    {"dimension_contribution", "segment_stability", "metric_monitor", "trend_analysis"}
)


class DateRange(NamedTuple):
    start: date | None
    end: date | None


class HistoricalLookupEngine:
    """Filter stored findings by metric, dimension, type, and date range."""

    def __init__(self, session: Session) -> None:
        self._findings = FindingRepository(session)

    def lookup(
        self,
        *,
        metric_name: str | None = None,
        dimension_name: str | None = None,
        dimension_value: str | None = None,
        finding_type: str | None = None,
        date_range: DateRange | None = None,
        limit: int = 500,
    ) -> list[StoredFinding]:
        date_from, date_to = _date_range_to_datetimes(date_range)
        filters = FindingSearchFilters(
            metric_name=metric_name,
            dimension_name=dimension_name,
            dimension_value=dimension_value,
            finding_type=finding_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
        return self._findings.search(filters)

    def lookup_deterioration(
        self,
        *,
        dimension_name: str,
        dimension_value: str,
        metric_name: str | None = None,
        date_range: DateRange | None = None,
        limit: int = 200,
    ) -> list[StoredFinding]:
        """Findings for a dimension where delta_pp indicates deterioration."""
        rows = self.lookup(
            metric_name=metric_name,
            dimension_name=dimension_name,
            dimension_value=dimension_value,
            date_range=date_range,
            limit=limit,
        )
        return [r for r in rows if _is_deterioration(r)]

    def frequency_by_investigation(
        self, findings: list[StoredFinding]
    ) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for f in findings:
            counter[f.investigation_id] += 1
        return dict(counter)


def _is_deterioration(finding: StoredFinding) -> bool:
    if finding.finding_type not in DETERIORATION_FINDING_TYPES:
        return False
    if finding.delta_pp is not None and finding.delta_pp < 0:
        return True
    if finding.contribution_pp is not None and finding.contribution_pp < 0:
        return True
    summary = (finding.summary or "").lower()
    return "deterioration" in summary or "恶化" in summary


def _date_range_to_datetimes(
    date_range: DateRange | None,
) -> tuple[datetime | None, datetime | None]:
    if date_range is None:
        return None, None
    date_from = None
    date_to = None
    if date_range.start is not None:
        date_from = datetime.combine(date_range.start, time.min, tzinfo=timezone.utc)
    if date_range.end is not None:
        date_to = datetime.combine(date_range.end, time.max, tzinfo=timezone.utc)
    return date_from, date_to
