"""Replay timeline events for investigation playback."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ReplayEventKind = Literal[
    "workflow_started",
    "skill_started",
    "skill_completed",
    "skill_skipped",
    "skill_failed",
    "finding_discovered",
    "workflow_completed",
    "report_generated",
]

ReplayEventCategory = Literal["workflow", "skill", "finding", "report"]


class ReplayTimelineEvent(BaseModel):
    """Single ordered event for step-by-step investigation replay."""

    event_id: str
    sequence_index: int
    timestamp: datetime
    event_kind: ReplayEventKind
    category: ReplayEventCategory
    skill_name: Optional[str] = None
    execution_status: Optional[str] = None
    title: str = ""
    summary: str = ""
    duration_ms: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class InvestigationReplay(BaseModel):
    """Full replay session derived from a completed investigation."""

    investigation_id: str
    workflow_id: str
    metric_name: str
    goal: str = ""
    workflow_status: str = ""
    total_events: int = 0
    events: List[ReplayTimelineEvent] = Field(default_factory=list)
    executed_skills: List[str] = Field(default_factory=list)
    generated_at: Optional[datetime] = None
