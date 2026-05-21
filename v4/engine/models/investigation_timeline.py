"""Investigation timeline events for workspace UI."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SkillName = Literal[
    "metric_monitor",
    "trend_analysis",
    "dimension_contribution",
    "segment_stability",
    "strategy_impact",
    "finding_summary",
    "report_builder",
]

ExecutionStatus = Literal["pending", "running", "completed", "skipped", "failed"]


class InvestigationTimelineEvent(BaseModel):
    timestamp: datetime
    skill_name: SkillName
    execution_status: ExecutionStatus
    summary: str = ""
    duration_ms: int | None = None
    step_order: int = 0
