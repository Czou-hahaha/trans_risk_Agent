"""Input schema for dimension contribution skill."""

from datetime import date

from pydantic import BaseModel, Field

DEFAULT_TOP_N = 5


class PeriodRange(BaseModel):
    start_date: date
    end_date: date


class DimensionContributionInput(BaseModel):
    metric_name: str
    current_period: PeriodRange
    previous_period: PeriodRange
    dimension_list: list[str]
    top_n: int = Field(default=DEFAULT_TOP_N, ge=1, le=50)
