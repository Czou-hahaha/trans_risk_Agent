"""Parse investigation goal text into metric name."""

from __future__ import annotations

import re

_METRIC_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"fpd7", re.I), "fpd7"),
    (re.compile(r"fpd30", re.I), "fpd30"),
    (re.compile(r"d0", re.I), "d0"),
    (re.compile(r"m1", re.I), "m1"),
    (re.compile(r"roll", re.I), "roll_rate"),
]


def parse_metric_from_goal(goal: str, default: str = "fpd7") -> str:
    """Extract metric name from natural-language goal."""
    for pattern, metric in _METRIC_PATTERNS:
        if pattern.search(goal):
            return metric
    return default
