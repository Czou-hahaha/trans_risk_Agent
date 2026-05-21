"""趋势分析用时间序列聚合（SQL 仅在此层）。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.exceptions import MetricQueryError
from tools.db.contribution.models.metric_breakdowns import MetricBreakdown
from tools.db.monitor.models.metrics_daily import MetricsDaily

logger = logging.getLogger(__name__)

DIMENSION_COLUMNS = frozenset({"channel", "score_band", "product", "region"})


@dataclass(frozen=True)
class TimeSeriesPoint:
    event_date: date
    metric_value: float
    sample_size: int
    period_label: str


class TrendRepository:
    """从宽表/长表聚合 event_date 级序列；skill 层不写 SQL。"""

    def __init__(self, monitor_session: Session, contribution_session: Session | None = None) -> None:
        self._monitor = monitor_session
        self._contribution = contribution_session

    def fetch_aggregated_series(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
        aggregation_level: str = "day",
        *,
        channel: str | None = None,
        score_band: str | None = None,
        product: str | None = None,
        region: str | None = None,
    ) -> list[TimeSeriesPoint]:
        filters = {
            k: v
            for k, v in {
                "channel": channel,
                "score_band": score_band,
                "product": product,
                "region": region,
            }.items()
            if v is not None
        }
        if filters:
            if self._contribution is None:
                raise ValueError("带维度筛选时必须提供 contribution 库 session")
            daily = self._fetch_breakdown_daily(
                metric_name, start_date, end_date, filters
            )
        else:
            daily = self._fetch_portfolio_daily(metric_name, start_date, end_date)

        if daily.empty:
            return []

        if aggregation_level == "day":
            return self._to_daily_points(daily)
        if aggregation_level == "week":
            return self._aggregate_weekly(daily)
        raise ValueError(f"不支持的 aggregation_level: {aggregation_level}")

    def _fetch_portfolio_daily(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        stmt = (
            select(
                MetricsDaily.metric_date.label("event_date"),
                MetricsDaily.metric_value,
            )
            .where(
                MetricsDaily.metric_name == metric_name,
                MetricsDaily.metric_date >= start_date,
                MetricsDaily.metric_date <= end_date,
            )
            .order_by(MetricsDaily.metric_date)
        )
        try:
            rows = self._monitor.execute(stmt).all()
        except SQLAlchemyError as exc:
            logger.error(
                "metrics_daily 趋势查询失败 metric=%s range=%s..%s",
                metric_name,
                start_date,
                end_date,
                exc_info=True,
            )
            raise MetricQueryError(
                f"查询指标 '{metric_name}' 失败：{start_date} ~ {end_date}"
            ) from exc

        if not rows:
            return pd.DataFrame(columns=["event_date", "metric_value", "sample_size"])
        df = pd.DataFrame(rows, columns=["event_date", "metric_value"])
        df["sample_size"] = 1
        return df

    def _fetch_breakdown_daily(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
        filters: dict[str, str],
    ) -> pd.DataFrame:
        session = self._contribution
        assert session is not None
        frames: list[pd.DataFrame] = []
        for dim_name, dim_value in filters.items():
            if dim_name not in DIMENSION_COLUMNS:
                continue
            stmt = (
                select(
                    MetricBreakdown.metric_date.label("event_date"),
                    MetricBreakdown.metric_value,
                    MetricBreakdown.sample_size,
                )
                .where(
                    MetricBreakdown.metric_name == metric_name,
                    MetricBreakdown.dimension_name == dim_name,
                    MetricBreakdown.dimension_value == dim_value,
                    MetricBreakdown.metric_date >= start_date,
                    MetricBreakdown.metric_date <= end_date,
                )
                .order_by(MetricBreakdown.metric_date)
            )
            try:
                rows = session.execute(stmt).all()
            except SQLAlchemyError as exc:
                logger.error(
                    "metric_breakdowns 趋势查询失败 metric=%s %s=%s",
                    metric_name,
                    dim_name,
                    dim_value,
                    exc_info=True,
                )
                raise MetricQueryError(
                    f"维度查询失败 {dim_name}={dim_value}"
                ) from exc
            if rows:
                frames.append(
                    pd.DataFrame(rows, columns=["event_date", "metric_value", "sample_size"])
                )

        if not frames:
            return pd.DataFrame(columns=["event_date", "metric_value", "sample_size"])
        if len(frames) == 1:
            return frames[0]
        merged = frames[0]
        for other in frames[1:]:
            merged = merged.merge(other, on="event_date", suffixes=("", "_r"))
            w_num = merged["metric_value"] * merged["sample_size"]
            w_den = merged["sample_size"]
            w_num_r = merged["metric_value_r"] * merged["sample_size_r"]
            w_den_r = merged["sample_size_r"]
            total_w = w_den + w_den_r
            merged["metric_value"] = (w_num + w_num_r) / total_w
            merged["sample_size"] = total_w.astype(int)
            merged = merged[["event_date", "metric_value", "sample_size"]]
        return merged

    @staticmethod
    def _to_daily_points(df: pd.DataFrame) -> list[TimeSeriesPoint]:
        points: list[TimeSeriesPoint] = []
        for row in df.itertuples(index=False):
            event_date = row.event_date
            label = event_date.isoformat()
            points.append(
                TimeSeriesPoint(
                    event_date=event_date,
                    metric_value=float(row.metric_value),
                    sample_size=int(row.sample_size),
                    period_label=label,
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

    @staticmethod
    def window_start(end_date: date, window_days: int) -> date:
        return end_date - timedelta(days=window_days - 1)
