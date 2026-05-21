"""Investigation orchestration entrypoints."""

from workflow.investigation_workflow import InvestigationWorkflow

InvestigationOrchestrator = InvestigationWorkflow

__all__ = ["InvestigationOrchestrator", "InvestigationWorkflow"]
