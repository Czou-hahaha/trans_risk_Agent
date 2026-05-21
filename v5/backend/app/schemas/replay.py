"""API schemas for investigation replay."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReplayTimelineEventOut(BaseModel):
    event_id: str
    sequence_index: int
    timestamp: datetime
    event_kind: str
    category: str
    skill_name: Optional[str] = None
    execution_status: Optional[str] = None
    title: str = ""
    summary: str = ""
    duration_ms: Optional[int] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class InvestigationReplayOut(BaseModel):
    investigation_id: UUID
    workflow_id: str
    metric_name: str
    goal: str = ""
    workflow_status: str = ""
    status: str = ""
    total_events: int = 0
    events: list[ReplayTimelineEventOut] = Field(default_factory=list)
    executed_skills: list[str] = Field(default_factory=list)
    generated_at: Optional[datetime] = None
