"""Workflow lifecycle status values."""

from enum import Enum


class WorkflowStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_NO_ISSUE = "completed_no_issue"
    FAILED = "failed"
