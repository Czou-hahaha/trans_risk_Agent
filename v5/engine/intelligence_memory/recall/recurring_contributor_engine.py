"""Detect contributors that repeatedly rank among top contributors."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from intelligence_memory.recall.historical_lookup_engine import DateRange
from intelligence_memory.recall.schemas.recurring_pattern import RecurringPattern
from intelligence_memory.repositories.finding_repository import (
    FindingRepository,
    FindingSearchFilters,
)
from intelligence_memory.schemas.stored_finding import StoredFinding

logger = logging.getLogger(__name__)

CONTRIBUTOR_FINDING_TYPE = "dimension_contribution"


class RecurringContributorEngine:
    """Identify dimension values that appear in top contributors across runs."""

    def __init__(self, session: Session) -> None:
        self._findings = FindingRepository(session)

    def detect(
        self,
        *,
        window_days: int = 30,
        min_occurrences: int = 3,
        top_n: int = 3,
        metric_name: str | None = None,
        reference_date: date | None = None,
    ) -> list[RecurringPattern]:
        ref = reference_date or datetime.now(timezone.utc).date()
        window_start = ref - timedelta(days=window_days)
        date_from = datetime.combine(window_start, time.min, tzinfo=timezone.utc)

        filters = FindingSearchFilters(
            metric_name=metric_name,
            finding_type=CONTRIBUTOR_FINDING_TYPE,
            date_from=date_from,
            limit=5000,
        )
        rows = self._findings.search(filters)
        if not rows:
            return []

        by_investigation: dict[str, list[StoredFinding]] = defaultdict(list)
        for row in rows:
            if row.dimension_name and row.dimension_value:
                by_investigation[row.investigation_id].append(row)

        contributor_hits: dict[tuple[str, str, str | None], set[str]] = defaultdict(set)
        for inv_id, inv_findings in by_investigation.items():
            top = _top_contributors(inv_findings, top_n=top_n)
            for finding in top:
                key = (
                    finding.dimension_name or "",
                    finding.dimension_value or "",
                    finding.metric_name,
                )
                contributor_hits[key].add(inv_id)

        patterns: list[RecurringPattern] = []
        for (dim_name, dim_value, met), inv_ids in sorted(
            contributor_hits.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        ):
            count = len(inv_ids)
            if count < min_occurrences:
                continue
            patterns.append(
                RecurringPattern(
                    pattern_type="recurring_contributor",
                    dimension_name=dim_name,
                    dimension_value=dim_value,
                    metric_name=met,
                    occurrence_count=count,
                    investigation_ids=sorted(inv_ids),
                    window_days=window_days,
                    min_occurrences=min_occurrences,
                    summary=(
                        f"{dim_value} appeared in top {top_n} contributors "
                        f"{count} times in the last {window_days} days"
                    ),
                )
            )
        return patterns


def _top_contributors(
    findings: list[StoredFinding], *, top_n: int
) -> list[StoredFinding]:
    ranked = sorted(
        findings,
        key=lambda f: abs(f.contribution_pp or 0.0),
        reverse=True,
    )
    return ranked[:top_n]
