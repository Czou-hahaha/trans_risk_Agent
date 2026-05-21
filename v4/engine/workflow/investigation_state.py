"""Investigation workflow lifecycle and per-skill execution state."""

from enum import Enum


class WorkflowStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_NO_ISSUE = "completed_no_issue"
    FAILED = "failed"


class SkillExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
