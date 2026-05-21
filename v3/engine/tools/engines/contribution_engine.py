"""Pure contribution math — no workflow, severity, or attribution semantics."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PeriodAggregate:
    dimension_value: str
    metric_rate: float
    sample_size: int
    volume_share: float


@dataclass(frozen=True)
class ContributorRow:
    dimension_name: str
    dimension_value: str
    current_rate: float
    previous_rate: float
    delta_pp: float
    contribution_pp: float
    current_volume: int
    previous_volume: int
    volume_share: float


class ContributionEngine:
    """Generic volume-weighted contribution decomposition."""

    @staticmethod
    def aggregate_period(df: pd.DataFrame) -> dict[str, PeriodAggregate]:
        if df.empty:
            return {}

        work = df.copy()
        work["_weighted"] = work["metric_value"] * work["sample_size"]
        grouped = (
            work.groupby("dimension_value", as_index=True)
            .agg(metric_rate=("_weighted", "sum"), sample_size=("sample_size", "sum"))
            .reset_index()
        )
        grouped["metric_rate"] = grouped["metric_rate"] / grouped["sample_size"].clip(
            lower=1
        )
        total_volume = int(grouped["sample_size"].sum())
        if total_volume <= 0:
            logger.warning("aggregate_period: total sample_size is zero")
            return {}

        result: dict[str, PeriodAggregate] = {}
        for row in grouped.itertuples(index=False):
            share = float(row.sample_size) / total_volume
            result[str(row.dimension_value)] = PeriodAggregate(
                dimension_value=str(row.dimension_value),
                metric_rate=float(row.metric_rate),
                sample_size=int(row.sample_size),
                volume_share=round(share, 6),
            )
        return result

    @staticmethod
    def calculate_delta_pp(current_rate: float, previous_rate: float) -> float:
        return round((current_rate - previous_rate) * 100, 4)

    @staticmethod
    def calculate_contribution_pp(
        current_rate: float,
        previous_rate: float,
        volume_share: float,
    ) -> float:
        delta_rate = current_rate - previous_rate
        return round(delta_rate * volume_share * 100, 4)

    @staticmethod
    def calculate_contribution(
        current_rate: float,
        previous_rate: float,
        volume_share: float,
    ) -> tuple[float, float]:
        delta_pp = ContributionEngine.calculate_delta_pp(current_rate, previous_rate)
        contribution_pp = ContributionEngine.calculate_contribution_pp(
            current_rate, previous_rate, volume_share
        )
        return delta_pp, contribution_pp

    @staticmethod
    def compare_periods(
        dimension_name: str,
        current: dict[str, PeriodAggregate],
        previous: dict[str, PeriodAggregate],
    ) -> list[ContributorRow]:
        all_values = sorted(set(current) | set(previous))
        rows: list[ContributorRow] = []

        for value in all_values:
            cur = current.get(value)
            prev = previous.get(value)
            cur_rate = cur.metric_rate if cur else 0.0
            prev_rate = prev.metric_rate if prev else 0.0
            share = cur.volume_share if cur else 0.0
            delta_pp, contribution_pp = ContributionEngine.calculate_contribution(
                cur_rate, prev_rate, share
            )
            rows.append(
                ContributorRow(
                    dimension_name=dimension_name,
                    dimension_value=value,
                    current_rate=cur_rate,
                    previous_rate=prev_rate,
                    delta_pp=delta_pp,
                    contribution_pp=contribution_pp,
                    current_volume=cur.sample_size if cur else 0,
                    previous_volume=prev.sample_size if prev else 0,
                    volume_share=share,
                )
            )
        return rows

    @staticmethod
    def rank_by_contribution(
        rows: list[ContributorRow],
        *,
        top_n: int,
        descending: bool = True,
    ) -> list[ContributorRow]:
        """Sort by contribution_pp; caller chooses direction."""
        return sorted(rows, key=lambda r: r.contribution_pp, reverse=descending)[:top_n]

    @staticmethod
    def rank_by_abs_contribution(
        rows: list[ContributorRow],
        *,
        top_n: int,
    ) -> list[ContributorRow]:
        return sorted(
            rows, key=lambda r: abs(r.contribution_pp), reverse=True
        )[:top_n]

    @staticmethod
    def rate_to_percent_points(rate: float) -> float:
        return round(rate * 100, 4)

    @staticmethod
    def portfolio_weighted_rate(aggregates: dict[str, PeriodAggregate]) -> float | None:
        if not aggregates:
            return None
        total_vol = sum(a.sample_size for a in aggregates.values())
        if total_vol <= 0:
            return None
        weighted = sum(a.metric_rate * a.sample_size for a in aggregates.values())
        return weighted / total_vol

    @staticmethod
    def max_volume_share(aggregates: dict[str, PeriodAggregate]) -> float:
        if not aggregates:
            return 0.0
        return max(a.volume_share for a in aggregates.values())

    @staticmethod
    def is_attributable_period(
        aggregates: dict[str, PeriodAggregate],
        *,
        dominance_threshold: float = 0.98,
    ) -> bool:
        """False when one segment accounts for ≥ threshold of period volume."""
        if not aggregates:
            return False
        if len(aggregates) <= 1:
            return False
        return ContributionEngine.max_volume_share(aggregates) < dominance_threshold

    @staticmethod
    def filter_attributable_contributors(
        rows: list[ContributorRow],
        *,
        dominance_threshold: float = 0.98,
    ) -> list[ContributorRow]:
        """Drop segments that dominate the current-period mix (composition, not driver)."""
        return [
            row
            for row in rows
            if row.volume_share < dominance_threshold
        ]
