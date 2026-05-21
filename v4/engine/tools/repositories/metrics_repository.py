"""Repository for metrics_daily time-series queries."""

import logging
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.exceptions import MetricQueryError
from tools.db.monitor.models.metrics_daily import MetricsDaily

logger = logging.getLogger(__name__)


class MetricsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def fetch_metric_series(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Return daily metric values in [start_date, end_date] inclusive."""
        stmt = (
            select(MetricsDaily.metric_date, MetricsDaily.metric_value)
            .where(
                MetricsDaily.metric_name == metric_name,
                MetricsDaily.metric_date >= start_date,
                MetricsDaily.metric_date <= end_date,
            )
            .order_by(MetricsDaily.metric_date)
        )
        try:
            rows = self._session.execute(stmt).all()
        except SQLAlchemyError as exc:
            logger.error(
                "metrics_daily query failed metric=%s range=%s..%s",
                metric_name,
                start_date,
                end_date,
                exc_info=True,
            )
            raise MetricQueryError(
                f"Failed to query metric '{metric_name}' "
                f"between {start_date} and {end_date}"
            ) from exc
        if not rows:
            return pd.DataFrame(columns=["metric_date", "metric_value"])
        return pd.DataFrame(rows, columns=["metric_date", "metric_value"])

    def fetch_metric_series_as_dicts(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        df = self.fetch_metric_series(metric_name, start_date, end_date)
        if df.empty:
            return []
        return df.to_dict(orient="records")
