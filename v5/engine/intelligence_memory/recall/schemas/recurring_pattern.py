"""Schema for recurring contributor / segment patterns."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecurringPattern(BaseModel):
    """A contributor or segment that appears repeatedly across investigations."""

    pattern_type: str = Field(
        description="e.g. recurring_contributor, recurring_segment"
    )
    dimension_name: str
    dimension_value: str
    metric_name: str | None = None
    occurrence_count: int
    investigation_ids: list[str] = Field(default_factory=list)
    window_days: int
    min_occurrences: int
    summary: str
