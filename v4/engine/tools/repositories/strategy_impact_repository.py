"""策略指标日表查询（SQL 仅在此层）。"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.exceptions import StrategyDataNotFoundError, StrategyQueryError
from tools.db.monitor.models.strategy_metrics_daily import StrategyMetricsDaily
from tools.engines.strategy_impact_engine import DailyMetricObservation

logger = logging.getLogger(__name__)


class StrategyImpactRepository:
    """拉取策略在 before/after 窗口内的日粒度指标。"""

    def __init__(self, monitor_session: Session) -> None:
        self._session = monitor_session

    def fetch_strategy_observations(
        self,
        strategy_name: str,
        deployment_date: date,
        before_window_days: int,
        after_window_days: int,
        metric_names: list[str],
    ) -> list[DailyMetricObservation]:
        start, end = self.analysis_date_range(
            deployment_date=deployment_date,
            before_window_days=before_window_days,
            after_window_days=after_window_days,
        )
        stmt = (
            select(
                StrategyMetricsDaily.metric_date,
                StrategyMetricsDaily.metric_name,
                StrategyMetricsDaily.metric_value,
                StrategyMetricsDaily.sample_size,
            )
            .where(
                StrategyMetricsDaily.strategy_name == strategy_name,
                StrategyMetricsDaily.metric_date >= start,
                StrategyMetricsDaily.metric_date <= end,
                StrategyMetricsDaily.metric_name.in_(metric_names),
            )
            .order_by(StrategyMetricsDaily.metric_date, StrategyMetricsDaily.metric_name)
        )
        try:
            rows = self._session.execute(stmt).all()
        except SQLAlchemyError as exc:
            logger.error(
                "strategy_metrics_daily 查询失败 strategy=%s range=%s..%s",
                strategy_name,
                start,
                end,
                exc_info=True,
            )
            raise StrategyQueryError(
                f"查询策略指标失败 strategy={strategy_name}"
            ) from exc

        if not rows:
            raise StrategyDataNotFoundError(
                f"策略 '{strategy_name}' 在 {start}..{end} 无指标数据"
            )

        return [
            DailyMetricObservation(
                event_date=row.metric_date,
                metric_name=row.metric_name,
                metric_value=float(row.metric_value),
                sample_size=int(row.sample_size),
            )
            for row in rows
        ]

    @staticmethod
    def analysis_date_range(
        *,
        deployment_date: date,
        before_window_days: int,
        after_window_days: int,
    ) -> tuple[date, date]:
        start = deployment_date - timedelta(days=before_window_days)
        end = deployment_date + timedelta(days=after_window_days - 1)
        return start, end
