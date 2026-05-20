"""Load metrics_daily and metric_breakdowns from base_data_trans PKL."""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import delete

_V1 = Path(__file__).resolve().parents[2]
if str(_V1) not in sys.path:
    sys.path.insert(0, str(_V1))

from tools.db.contribution.models.metric_breakdowns import MetricBreakdown
from tools.db.contribution.session import SessionLocal as ContributionSession
from tools.db.contribution.session import ensure_database_exists as ensure_contribution_db
from tools.db.contribution.session import init_db as init_contribution_db
from tools.db.monitor.models.metrics_daily import MetricsDaily
from tools.db.monitor.session import SessionLocal as MonitorSession
from tools.db.monitor.session import ensure_database_exists as ensure_monitor_db
from tools.db.monitor.session import init_db as init_monitor_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PKL = _V1.parent / "base_data_trans_260323_base_v1.pkl"
FPD7_METRIC = "fpd7"
PASS_METRIC = "order_pass_rate"
BREAKDOWN_DIMENSIONS = ("order_tag", "risk_level", "cus_type", "floan_period")


def resolve_pkl_path(path: Path | None = None) -> Path:
    candidate = path or DEFAULT_PKL
    if not candidate.is_file():
        raise FileNotFoundError(f"PKL not found: {candidate}")
    return candidate


def load_transactions(pkl_path: Path) -> pd.DataFrame:
    df = pd.read_pickle(pkl_path)
    df["apply_date"] = pd.to_datetime(df["apply_date"], errors="coerce").dt.date
    df = df.dropna(subset=["apply_date"])
    logger.info(
        "Loaded PKL rows=%d apply_date=%s..%s",
        len(df),
        df["apply_date"].min(),
        df["apply_date"].max(),
    )
    return df


def _fpd7_daily_rates(fpd: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        fpd.groupby("apply_date", as_index=False)
        .agg(
            overdue_amt=("if_fpd7_overdue_amt", "sum"),
            show_amt=("if_fpd7_show_amt", "sum"),
        )
        .sort_values("apply_date")
    )
    grouped["metric_value"] = grouped["overdue_amt"] / grouped["show_amt"].clip(lower=1e-9)
    return grouped[["apply_date", "metric_value"]]


def build_metrics_daily(df: pd.DataFrame) -> list[tuple[str, date, float]]:
    rows: list[tuple[str, date, float]] = []

    fpd = df[df["if_fpd7_show"] == 1].copy()
    if not fpd.empty:
        for _, r in _fpd7_daily_rates(fpd).iterrows():
            rows.append((FPD7_METRIC, r["apply_date"], float(r["metric_value"])))

    pass_daily = (
        df.groupby("apply_date", as_index=False)["if_pass"]
        .mean()
        .rename(columns={"if_pass": "metric_value"})
    )
    for _, r in pass_daily.iterrows():
        rows.append((PASS_METRIC, r["apply_date"], float(r["metric_value"])))

    return rows


def build_metric_breakdowns(df: pd.DataFrame) -> list[tuple[date, str, str, float, int]]:
    fpd = df[df["if_fpd7_show"] == 1].copy()
    if fpd.empty:
        return []

    out: list[tuple[date, str, str, float, int]] = []
    for dim in BREAKDOWN_DIMENSIONS:
        if dim not in fpd.columns:
            logger.warning("Dimension column missing, skip: %s", dim)
            continue
        work = fpd.dropna(subset=[dim])
        grouped = (
            work.groupby(["apply_date", dim], as_index=False)
            .agg(
                overdue_amt=("if_fpd7_overdue_amt", "sum"),
                show_amt=("if_fpd7_show_amt", "sum"),
                sample_size=("if_fpd7_show", "count"),
            )
            .sort_values(["apply_date", dim])
        )
        grouped["metric_value"] = grouped["overdue_amt"] / grouped["show_amt"].clip(lower=1e-9)
        for row in grouped.itertuples(index=False):
            out.append(
                (
                    row.apply_date,
                    dim,
                    str(getattr(row, dim)),
                    float(row.metric_value),
                    int(row.sample_size),
                )
            )
    return out


def latest_fpd7_observable_date(df: pd.DataFrame) -> date | None:
    fpd = df[df["if_fpd7_show"] == 1]
    if fpd.empty:
        return None
    return fpd["apply_date"].max()


def seed_from_pkl(pkl_path: Path | None = None) -> dict[str, object]:
    path = resolve_pkl_path(pkl_path)
    df = load_transactions(path)

    metrics_rows = build_metrics_daily(df)
    breakdown_rows = build_metric_breakdowns(df)
    ref_date = latest_fpd7_observable_date(df)

    ensure_monitor_db()
    init_monitor_db()
    ensure_contribution_db()
    init_contribution_db()

    with MonitorSession() as db:
        db.execute(delete(MetricsDaily))
        for metric_name, metric_date, metric_value in metrics_rows:
            db.add(
                MetricsDaily(
                    metric_name=metric_name,
                    metric_date=metric_date,
                    metric_value=metric_value,
                )
            )
        db.commit()

    with ContributionSession() as db:
        db.execute(delete(MetricBreakdown))
        for metric_date, dim_name, dim_value, metric_value, sample_size in breakdown_rows:
            db.add(
                MetricBreakdown(
                    metric_name=FPD7_METRIC,
                    metric_date=metric_date,
                    dimension_name=dim_name,
                    dimension_value=dim_value,
                    metric_value=metric_value,
                    sample_size=sample_size,
                )
            )
        db.commit()

    summary = {
        "pkl_path": str(path),
        "apply_date_min": df["apply_date"].min(),
        "apply_date_max": df["apply_date"].max(),
        "metrics_daily_rows": len(metrics_rows),
        "breakdown_rows": len(breakdown_rows),
        "fpd7_reference_date": ref_date,
        "breakdown_dimensions": list(BREAKDOWN_DIMENSIONS),
    }
    logger.info("PKL seed complete: %s", summary)
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed PostgreSQL from transaction PKL")
    parser.add_argument("--pkl", type=Path, default=None)
    args = parser.parse_args()
    seed_from_pkl(args.pkl)
