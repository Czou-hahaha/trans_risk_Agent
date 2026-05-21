"""Segment 稳定性用时间序列聚合（SQL 仅在此层）。"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import distinct, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.exceptions import BreakdownQueryError
from tools.db.contribution.models.metric_breakdowns import MetricBreakdown
from tools.repositories.trend_repository import TimeSeriesPoint

logger = logging.getLogger(__name__)

SUPPORTED_DIMENSIONS = frozenset(
    {"channel", "score_band", "product", "region", "user_segment"}
)


class SegmentStabilityRepository:
    """按 dimension 拉取各 segment 的日/周序列；skill 层不写 SQL。"""

    def __init__(self, contribution_session: Session) -> None:
        self._session = contribution_session

    def fetch_all_segment_series(
        self,
        metric_name: str,
        dimension_name: str,
        start_date: date,
        end_date: date,
        aggregation_level: str = "week",
    ) -> dict[str, list[TimeSeriesPoint]]:
        if dimension_name not in SUPPORTED_DIMENSIONS:
            raise ValueError(
                f"不支持的 dimension_name={dimension_name!r}，"
                f"允许: {sorted(SUPPORTED_DIMENSIONS)}"
            )

        stmt = (
            select(
                MetricBreakdown.metric_date.label("event_date"),
                MetricBreakdown.dimension_value,
                MetricBreakdown.metric_value,
                MetricBreakdown.sample_size,
            )
            .where(
                MetricBreakdown.metric_name == metric_name,
                MetricBreakdown.dimension_name == dimension_name,
                MetricBreakdown.metric_date >= start_date,
                MetricBreakdown.metric_date <= end_date,
            )
            .order_by(MetricBreakdown.dimension_value, MetricBreakdown.metric_date)
        )
        try:
            rows = self._session.execute(stmt).all()
        except SQLAlchemyError as exc:
            logger.error(
                "segment stability 批量查询失败 metric=%s dimension=%s range=%s..%s",
                metric_name,
                dimension_name,
                start_date,
                end_date,
                exc_info=True,
            )
            raise BreakdownQueryError(
                f"查询 segment 序列失败 metric={metric_name} dimension={dimension_name}"
            ) from exc

        if not rows:
            return {}

        df = pd.DataFrame(
            rows,
            columns=["event_date", "dimension_value", "metric_value", "sample_size"],
        )
        result: dict[str, list[TimeSeriesPoint]] = {}
        for dim_value, group in df.groupby("dimension_value", sort=True):
            daily = group[["event_date", "metric_value", "sample_size"]].copy()
            if aggregation_level == "day":
                points = self._to_daily_points(daily)
            elif aggregation_level == "week":
                points = self._aggregate_weekly(daily)
            else:
                raise ValueError(f"不支持的 aggregation_level: {aggregation_level}")
            if len(points) >= 2:
                result[str(dim_value)] = points
        return result

    def list_dimension_values(
        self,
        metric_name: str,
        dimension_name: str,
        start_date: date,
        end_date: date,
    ) -> list[str]:
        stmt = (
            select(distinct(MetricBreakdown.dimension_value))
            .where(
                MetricBreakdown.metric_name == metric_name,
                MetricBreakdown.dimension_name == dimension_name,
                MetricBreakdown.metric_date >= start_date,
                MetricBreakdown.metric_date <= end_date,
            )
            .order_by(MetricBreakdown.dimension_value)
        )
        try:
            rows = self._session.execute(stmt).scalars().all()
        except SQLAlchemyError as exc:
            logger.error(
                "segment dimension values 查询失败 metric=%s dimension=%s",
                metric_name,
                dimension_name,
                exc_info=True,
            )
            raise BreakdownQueryError(
                f"查询 dimension values 失败 {dimension_name}"
            ) from exc
        return [str(v) for v in rows]

    @staticmethod
    def window_start(end_date: date, window_days: int) -> date:
        return end_date - timedelta(days=window_days - 1)

    @staticmethod
    def _to_daily_points(df: pd.DataFrame) -> list[TimeSeriesPoint]:
        points: list[TimeSeriesPoint] = []
        for row in df.itertuples(index=False):
            event_date = row.event_date
            points.append(
                TimeSeriesPoint(
                    event_date=event_date,
                    metric_value=float(row.metric_value),
                    sample_size=int(row.sample_size),
                    period_label=event_date.isoformat(),
                )
            )
        return points

    @staticmethod
    def _aggregate_weekly(df: pd.DataFrame) -> list[TimeSeriesPoint]:
        work = df.copy()
        work["event_date"] = pd.to_datetime(work["event_date"])
        iso = work["event_date"].dt.isocalendar()
        work["iso_year"] = iso.year.astype(int)
        work["iso_week"] = iso.week.astype(int)
        work["period_label"] = (
            work["iso_year"].astype(str)
            + "-W"
            + work["iso_week"].astype(str).str.zfill(2)
        )
        points: list[TimeSeriesPoint] = []
        keys = ["iso_year", "iso_week", "period_label"]
        for _, group in work.groupby(keys, sort=True):
            weights = group["sample_size"].astype(float)
            weighted_rate = (group["metric_value"] * weights).sum() / weights.sum()
            end = group["event_date"].max().date()
            points.append(
                TimeSeriesPoint(
                    event_date=end,
                    metric_value=float(weighted_rate),
                    sample_size=int(weights.sum()),
                    period_label=str(group["period_label"].iloc[0]),
                )
            )
        points.sort(key=lambda p: p.event_date)
        return points
