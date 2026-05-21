"""Standardized finding schema for metric monitor skill."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import Field

from models.base_finding import BaseFinding
from models.metric_profiles import MetricProfile


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MetricDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class InvestigationGate(str, Enum):
    SKIP = "skip"
    WATCH = "watch"
    INVESTIGATE = "investigate"


class AttributionHint(str, Enum):
    RISK_DETERIORATION = "risk_deterioration"
    RISK_IMPROVEMENT = "risk_improvement"
    NEUTRAL = "neutral"


class InvestigationTrigger(str, Enum):
    SINGLE_PERIOD_THRESHOLD = "single_period_threshold"
    CONSECUTIVE_WEEKS_TREND = "consecutive_weeks_trend"
    CONSECUTIVE_WEEKS_CUMULATIVE = "consecutive_weeks_cumulative"


class MetricMonitorFinding(BaseFinding):
    """Portfolio-level monitor finding — workflow gate and business severity live here."""

    finding_type: Literal["metric_monitor"] = "metric_monitor"
    metric_profile: MetricProfile
    current_value: float
    previous_value: float
    delta_pp: float
    prior_period_delta_pp: float | None = Field(
        default=None,
        description="Week-over-week delta for the period before previous (3rd window)",
    )
    change_rate: float | None = None
    direction: MetricDirection
    investigation_gate: InvestigationGate
    needs_investigation: bool = Field(
        description="True when portfolio rules require dimension attribution"
    )
    is_abnormal: bool = Field(
        description="Alias of needs_investigation for backward compatibility"
    )
    severity: Severity
    consecutive_weeks_trend: bool = Field(default=False)
    investigation_triggers: list[InvestigationTrigger] = Field(default_factory=list)
    attribution_hint: AttributionHint = Field(
        description="Suggested downstream attribution direction"
    )

    @property
    def summary_message(self) -> str:
        """Backward-compatible alias for summary."""
        return self.summary
