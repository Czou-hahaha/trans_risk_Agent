"""Seed metric_breakdowns for FPD7 deterioration attribution demo."""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import delete

from tools.db.contribution.models.metric_breakdowns import MetricBreakdown
from tools.db.contribution.session import SessionLocal, ensure_database_exists, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DATE = date(2026, 5, 17)
METRIC_NAME = "fpd7"

# (dimension_name, dimension_value, previous_rate, current_rate, daily_sample_size)
# partner_X: delta 0.013, share 0.35 → contribution_pp ≈ +0.45
# score_band 600-650: delta 0.010, share 0.22 → contribution_pp ≈ +0.22
SEGMENTS: list[tuple[str, str, float, float, int]] = [
    ("channel", "partner_X", 0.028, 0.041, 3500),
    ("channel", "partner_A", 0.021, 0.022, 2500),
    ("channel", "direct", 0.020, 0.020, 2000),
    ("channel", "organic", 0.019, 0.019, 2000),
    ("score_band", "600-650", 0.030, 0.040, 2200),
    ("score_band", "650-700", 0.023, 0.024, 3000),
    ("score_band", "700+", 0.018, 0.018, 4800),
    ("product", "cash_loan", 0.026, 0.026, 4000),
    ("product", "installment", 0.021, 0.021, 3500),
    ("product", "revolving", 0.019, 0.019, 2500),
    ("region", "east", 0.025, 0.025, 3500),
    ("region", "north", 0.020, 0.020, 3500),
    ("region", "south", 0.022, 0.022, 3000),
]


def _dates() -> list[date]:
    return [BASE_DATE - timedelta(days=i) for i in range(13, -1, -1)]


def _is_current_period(d: date) -> bool:
    """Last 7 days ending BASE_DATE are current; prior 7 are previous."""
    days_back = (BASE_DATE - d).days
    return days_back < 7


def seed_metric_breakdowns() -> int:
    ensure_database_exists()
    init_db()
    dates = _dates()
    count = 0

    with SessionLocal() as db:
        db.execute(delete(MetricBreakdown))
        for dim_name, dim_value, prev_rate, cur_rate, sample_size in SEGMENTS:
            for d in dates:
                rate = cur_rate if _is_current_period(d) else prev_rate
                db.add(
                    MetricBreakdown(
                        metric_name=METRIC_NAME,
                        metric_date=d,
                        dimension_name=dim_name,
                        dimension_value=dim_value,
                        metric_value=rate,
                        sample_size=sample_size,
                    )
                )
                count += 1
        db.commit()

    logger.info(
        "Seeded %d breakdown rows (%d segments x %d days)",
        count,
        len(SEGMENTS),
        len(dates),
    )
    return count


if __name__ == "__main__":
    seed_metric_breakdowns()
