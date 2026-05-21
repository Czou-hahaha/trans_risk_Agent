"""Metric-type profiles and per-type monitoring thresholds."""

from enum import Enum

from pydantic import BaseModel, Field


class MetricProfile(str, Enum):
    """Monitoring profile — gates and severity differ by business metric family."""

    SHORT_TERM_RISK = "short_term_risk"
    APPROVAL_RATE = "approval_rate"
    LONG_TERM_RISK = "long_term_risk"


class MetricThresholds(BaseModel):
    """Per-profile investigation and severity bands (units: percentage points)."""

    profile: MetricProfile
    investigate_pp: float = Field(description="|delta_pp| at or above → investigate")
    skip_pp: float = Field(
        description="|delta_pp| below this → skip unless consecutive-trend rule fires"
    )
    severity_high_pp: float
    severity_medium_pp: float
    consecutive_enabled: bool = True
    consecutive_cumulative_pp: float | None = Field(
        default=None,
        description="Long-term only: |d1|+|d2| same-direction sum triggers investigate",
    )
    risk_up_is_bad: bool = True


SHORT_TERM_RISK_METRICS = frozenset(
    {
        "fpd1",
        "fpd3",
        "fpd7",
        "fpd7_amt_overdue_rate",
        "fpd7_amt_overdue_rate_current_2w",
        "fpd7_amt_overdue_rate_prior_2w",
    }
)

APPROVAL_RATE_METRICS = frozenset(
    {
        "approval_rate",
        "order_pass_rate",
        "amt_pass_rate",
        "order_pass_rate_this_week",
        "order_pass_rate_last_week",
    }
)

LONG_TERM_RISK_METRICS = frozenset(
    {f"period{i}" for i in range(2, 9)}
    | {f"period{i}_order_overdue_rate" for i in range(2, 9)}
    | {f"period{i}_amt_overdue_rate" for i in range(2, 9)}
    | {"mob1", "mob2"}
)


PROFILE_THRESHOLDS: dict[MetricProfile, MetricThresholds] = {
    MetricProfile.SHORT_TERM_RISK: MetricThresholds(
        profile=MetricProfile.SHORT_TERM_RISK,
        skip_pp=1.0,
        investigate_pp=1.0,
        severity_medium_pp=1.0,
        severity_high_pp=1.5,
        consecutive_enabled=True,
        risk_up_is_bad=True,
    ),
    MetricProfile.APPROVAL_RATE: MetricThresholds(
        profile=MetricProfile.APPROVAL_RATE,
        skip_pp=2.0,
        investigate_pp=2.0,
        severity_medium_pp=2.0,
        severity_high_pp=4.0,
        consecutive_enabled=False,
        risk_up_is_bad=False,
    ),
    MetricProfile.LONG_TERM_RISK: MetricThresholds(
        profile=MetricProfile.LONG_TERM_RISK,
        skip_pp=2.0,
        investigate_pp=2.0,
        severity_medium_pp=2.0,
        severity_high_pp=3.5,
        consecutive_enabled=True,
        consecutive_cumulative_pp=2.5,
        risk_up_is_bad=True,
    ),
}


def resolve_metric_profile(metric_name: str) -> MetricProfile:
    """Map logical metric_name to monitoring profile."""
    key = metric_name.strip().lower()
    if key in SHORT_TERM_RISK_METRICS:
        return MetricProfile.SHORT_TERM_RISK
    if key in APPROVAL_RATE_METRICS:
        return MetricProfile.APPROVAL_RATE
    if key in LONG_TERM_RISK_METRICS:
        return MetricProfile.LONG_TERM_RISK
    if key.startswith("period") and any(c.isdigit() for c in key):
        return MetricProfile.LONG_TERM_RISK
    return MetricProfile.SHORT_TERM_RISK


def get_thresholds(profile: MetricProfile) -> MetricThresholds:
    return PROFILE_THRESHOLDS[profile]
