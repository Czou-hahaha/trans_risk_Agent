"""ORM model for per-strategy daily metrics (long format)."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from tools.db.monitor.base import Base


class StrategyMetricsDaily(Base):
    __tablename__ = "strategy_metrics_daily"
    __table_args__ = (
        UniqueConstraint(
            "strategy_name",
            "metric_date",
            "metric_name",
            name="uq_strategy_metrics_daily",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
