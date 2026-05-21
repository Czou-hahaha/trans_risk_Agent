"""Bridge backend API to engine replay layer."""

from __future__ import annotations

import logging
import sys
from uuid import UUID

from app.db.models import Investigation
from app.schemas.replay import InvestigationReplayOut, ReplayTimelineEventOut
from app.config import settings

logger = logging.getLogger(__name__)

_ENGINE = settings.engine_root
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from replay import ReplayBuilder  # noqa: E402


def build_investigation_replay(inv: Investigation) -> InvestigationReplayOut:
    """Build replay session from investigation report and metadata."""
    if inv.report is None or not inv.report.report_json:
        raise ValueError("Investigation report not available for replay")

    session = ReplayBuilder().build_from_payload(
        inv.report.report_json,
        goal=inv.goal,
    )
    return InvestigationReplayOut(
        investigation_id=inv.id,
        workflow_id=session.workflow_id,
        metric_name=session.metric_name,
        goal=session.goal or inv.goal,
        workflow_status=session.workflow_status,
        status=inv.status,
        total_events=session.total_events,
        events=[
            ReplayTimelineEventOut(
                event_id=e.event_id,
                sequence_index=e.sequence_index,
                timestamp=e.timestamp,
                event_kind=e.event_kind,
                category=e.category,
                skill_name=e.skill_name,
                execution_status=e.execution_status,
                title=e.title,
                summary=e.summary,
                duration_ms=e.duration_ms,
                payload=e.payload,
            )
            for e in session.events
        ],
        executed_skills=session.executed_skills,
        generated_at=session.generated_at,
    )
