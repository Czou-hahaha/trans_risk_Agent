"""Deterministic thresholds for investigation workflow routing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Default strategy impact probe (override via env/config later)
DEFAULT_STRATEGY_NAME = "RISK_003"
DEFAULT_STRATEGY_DEPLOYMENT_DATE = date(2026, 5, 10)
STRATEGY_DEPLOYMENT_NEARBY_DAYS = 45

CONTRIBUTOR_CONCENTRATION_PP = 0.35
TREND_DETERIORATION_DIRECTIONS = frozenset({"upward"})
TREND_DETERIORATION_STRENGTHS = frozenset({"moderate", "strong"})
UNSTABLE_SEGMENT_HEALTH = frozenset({"unstable", "deteriorating"})


@dataclass(frozen=True)
class WorkflowRuleConfig:
    contributor_concentration_pp: float = CONTRIBUTOR_CONCENTRATION_PP
    strategy_nearby_days: int = STRATEGY_DEPLOYMENT_NEARBY_DAYS
    default_strategy_name: str = DEFAULT_STRATEGY_NAME
    default_strategy_deployment: date = DEFAULT_STRATEGY_DEPLOYMENT_DATE


def strategy_deployment_nearby(
    analysis_date: date,
    deployment_date: date,
    *,
    window_days: int = STRATEGY_DEPLOYMENT_NEARBY_DAYS,
) -> bool:
    """True when analysis window overlaps post-deployment review period."""
    return abs((analysis_date - deployment_date).days) <= window_days
