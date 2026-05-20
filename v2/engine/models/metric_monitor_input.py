"""Input schema for metric monitor skill."""

from datetime import date

from pydantic import BaseModel, Field


class MetricMonitorInput(BaseModel):
    metric_name: str = Field(description="Logical metric name, e.g. fpd7, order_pass_rate")
    current_start_date: date = Field(description="Current period start (inclusive)")
    current_end_date: date = Field(description="Current period end (inclusive)")
    previous_start_date: date = Field(description="Previous period start (inclusive)")
    previous_end_date: date = Field(description="Previous period end (inclusive)")
    skip_threshold_pp: float | None = Field(
        default=None,
        description="Override profile skip threshold (pp); None = use metric profile default",
    )
    investigate_threshold_pp: float | None = Field(
        default=None,
        description="Override profile investigate threshold (pp); None = profile default",
    )
    risk_up_is_bad: bool | None = Field(
        default=None,
        description="Override polarity; None = from metric profile",
    )
    load_prior_period: bool = Field(
        default=True,
        description="Load third window for consecutive-weeks rules when profile supports it",
    )
