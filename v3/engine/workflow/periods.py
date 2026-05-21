"""Period window helpers for investigations."""

from __future__ import annotations

from datetime import date, timedelta

from workflow.constants import DEFAULT_PERIOD_DAYS


def resolve_period_windows(
    *,
    reference_date: date,
    period_days: int = DEFAULT_PERIOD_DAYS,
) -> tuple[tuple[date, date], tuple[date, date]]:
    def _window(days_back_end: int, length: int) -> tuple[date, date]:
        end = reference_date - timedelta(days=days_back_end)
        start = end - timedelta(days=length - 1)
        return start, end

    return _window(0, period_days), _window(period_days, period_days)
