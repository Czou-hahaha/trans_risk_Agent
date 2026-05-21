"""Seed demo metrics_daily data for metric monitor skill."""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import delete

from tools.db.monitor.models.metrics_daily import MetricsDaily
from tools.db.monitor.session import SessionLocal, ensure_database_exists, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DATE = date(2026, 5, 17)

# Previous 7d ~2.0%, current 7d ~4.3% → delta_pp ~ +2.3pp (triggers weekly investigate gate)
FPD7_VALUES = [
    0.020,
    0.020,
    0.020,
    0.020,
    0.020,
    0.020,
    0.020,
    0.038,
    0.040,
    0.042,
    0.044,
    0.044,
    0.046,
    0.048,
]

APPROVAL_RATE_VALUE = 0.72


def _dates() -> list[date]:
    return [BASE_DATE - timedelta(days=i) for i in range(13, -1, -1)]


def seed_metrics() -> int:
    ensure_database_exists()
    init_db()
    dates = _dates()
    count = 0
    with SessionLocal() as db:
        db.execute(delete(MetricsDaily))
        for i, d in enumerate(dates):
            db.add(
                MetricsDaily(
                    metric_name="fpd7",
                    metric_date=d,
                    metric_value=FPD7_VALUES[i],
                )
            )
            db.add(
                MetricsDaily(
                    metric_name="order_pass_rate",
                    metric_date=d,
                    metric_value=APPROVAL_RATE_VALUE,
                )
            )
            count += 2
        db.commit()
    logger.info("Seeded %d rows (%d days x 2 metrics)", count, len(dates))
    return count


if __name__ == "__main__":
    seed_metrics()
