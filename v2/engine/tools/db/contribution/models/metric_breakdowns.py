"""ORM model for dimension-level metric breakdowns (long format)."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from tools.db.contribution.base import Base


class MetricBreakdown(Base):
    __tablename__ = "metric_breakdowns"
    __table_args__ = (
        UniqueConstraint(
            "metric_name",
            "metric_date",
            "dimension_name",
            "dimension_value",
            name="uq_metric_breakdowns_grain",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    dimension_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dimension_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
