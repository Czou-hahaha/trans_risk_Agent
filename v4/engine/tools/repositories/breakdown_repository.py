"""Repository for metric_breakdowns dimension-level queries."""

import logging
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.exceptions import BreakdownQueryError
from tools.db.contribution.models.metric_breakdowns import MetricBreakdown

logger = logging.getLogger(__name__)


class BreakdownRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def query_dimension_breakdowns(
        self,
        metric_name: str,
        dimension_name: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Return daily breakdown rows for one dimension in [start_date, end_date]."""
        stmt = (
            select(
                MetricBreakdown.metric_date,
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
            .order_by(
                MetricBreakdown.dimension_value,
                MetricBreakdown.metric_date,
            )
        )
        try:
            rows = self._session.execute(stmt).all()
        except SQLAlchemyError as exc:
            logger.error(
                "metric_breakdowns query failed metric=%s dimension=%s range=%s..%s",
                metric_name,
                dimension_name,
                start_date,
                end_date,
                exc_info=True,
            )
            raise BreakdownQueryError(
                f"Failed to query breakdowns for metric '{metric_name}', "
                f"dimension '{dimension_name}' between {start_date} and {end_date}"
            ) from exc

        if not rows:
            return pd.DataFrame(
                columns=["metric_date", "dimension_value", "metric_value", "sample_size"]
            )
        return pd.DataFrame(
            rows,
            columns=["metric_date", "dimension_value", "metric_value", "sample_size"],
        )

    def query_metric_by_dimension(
        self,
        metric_name: str,
        dimension_name: str,
        dimension_value: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Return daily rows for a single dimension value."""
        stmt = (
            select(
                MetricBreakdown.metric_date,
                MetricBreakdown.metric_value,
                MetricBreakdown.sample_size,
            )
            .where(
                MetricBreakdown.metric_name == metric_name,
                MetricBreakdown.dimension_name == dimension_name,
                MetricBreakdown.dimension_value == dimension_value,
                MetricBreakdown.metric_date >= start_date,
                MetricBreakdown.metric_date <= end_date,
            )
            .order_by(MetricBreakdown.metric_date)
        )
        try:
            rows = self._session.execute(stmt).all()
        except SQLAlchemyError as exc:
            logger.error(
                "metric_breakdowns slice query failed metric=%s %s=%s range=%s..%s",
                metric_name,
                dimension_name,
                dimension_value,
                start_date,
                end_date,
                exc_info=True,
            )
            raise BreakdownQueryError(
                f"Failed to query {dimension_name}={dimension_value} for "
                f"metric '{metric_name}' between {start_date} and {end_date}"
            ) from exc

        if not rows:
            return pd.DataFrame(columns=["metric_date", "metric_value", "sample_size"])
        return pd.DataFrame(rows, columns=["metric_date", "metric_value", "sample_size"])
