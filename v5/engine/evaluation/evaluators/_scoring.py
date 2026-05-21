"""Shared deterministic scoring helpers."""

from __future__ import annotations

_ISSUE_WEIGHT = 0.12
_MAX_PENALTY = 1.0


def score_from_issues(issue_count: int, *, weight: float = _ISSUE_WEIGHT) -> float:
    """Map issue count to [0, 1] score."""
    penalty = min(_MAX_PENALTY, issue_count * weight)
    return round(max(0.0, 1.0 - penalty), 4)
