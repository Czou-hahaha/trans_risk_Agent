"""Tests for dimension dominance / attributability rules."""

from __future__ import annotations

import sys
from pathlib import Path

_V1 = Path(__file__).resolve().parents[1]
if str(_V1) not in sys.path:
    sys.path.insert(0, str(_V1))

from tools.engines.contribution_engine import (
    ContributionEngine,
    ContributorRow,
    PeriodAggregate,
)


def _agg(value: str, share: float, rate: float = 0.1, n: int = 1000) -> PeriodAggregate:
    return PeriodAggregate(
        dimension_value=value,
        metric_rate=rate,
        sample_size=n,
        volume_share=share,
    )


def test_rejects_single_segment_period() -> None:
    aggregates = {"only": _agg("only", 1.0)}
    assert not ContributionEngine.is_attributable_period(aggregates, dominance_threshold=0.98)


def test_rejects_dominant_segment_period() -> None:
    aggregates = {
        "a": _agg("a", 0.99),
        "b": _agg("b", 0.01, n=10),
    }
    assert not ContributionEngine.is_attributable_period(aggregates, dominance_threshold=0.98)


def test_accepts_balanced_period() -> None:
    aggregates = {
        "a": _agg("a", 0.6),
        "b": _agg("b", 0.4),
    }
    assert ContributionEngine.is_attributable_period(aggregates, dominance_threshold=0.98)


def test_filters_dominant_contributor_rows() -> None:
    rows = [
        ContributorRow(
            dimension_name="cus_type",
            dimension_value="老客",
            current_rate=0.1,
            previous_rate=0.12,
            delta_pp=-2.0,
            contribution_pp=-2.0,
            current_volume=1000,
            previous_volume=900,
            volume_share=1.0,
        ),
        ContributorRow(
            dimension_name="order_tag",
            dimension_value="online",
            current_rate=0.09,
            previous_rate=0.11,
            delta_pp=-2.0,
            contribution_pp=-0.5,
            current_volume=400,
            previous_volume=600,
            volume_share=0.4,
        ),
    ]
    kept = ContributionEngine.filter_attributable_contributors(
        rows, dominance_threshold=0.98
    )
    assert len(kept) == 1
    assert kept[0].dimension_name == "order_tag"
