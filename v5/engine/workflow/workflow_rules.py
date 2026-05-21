"""Workflow thresholds — loaded from v1/workflow_config when not overridden."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

from workflow.config_bridge import ensure_workflow_config_path

if TYPE_CHECKING:
    from workflow_config.schemas.workflow_config_schema import InvestigationWorkflowConfig

# Legacy fallbacks (used only when YAML load fails in tests)
CONTRIBUTOR_CONCENTRATION_PP = 0.35
STRATEGY_DEPLOYMENT_NEARBY_DAYS = 45
DEFAULT_STRATEGY_NAME = "RISK_003"
DEFAULT_STRATEGY_DEPLOYMENT_DATE = date(2026, 5, 10)
TREND_DETERIORATION_DIRECTIONS = frozenset({"upward"})
TREND_DETERIORATION_STRENGTHS = frozenset({"moderate", "strong", "weak"})
UNSTABLE_SEGMENT_HEALTH = frozenset({"unstable", "deteriorating"})


@dataclass(frozen=True)
class WorkflowRuleConfig:
    contributor_concentration_pp: float = CONTRIBUTOR_CONCENTRATION_PP
    strategy_nearby_days: int = STRATEGY_DEPLOYMENT_NEARBY_DAYS
    default_strategy_name: str = DEFAULT_STRATEGY_NAME
    default_strategy_deployment: date = DEFAULT_STRATEGY_DEPLOYMENT_DATE
    trend_deterioration_directions: frozenset[str] = TREND_DETERIORATION_DIRECTIONS
    trend_deterioration_strengths: frozenset[str] = TREND_DETERIORATION_STRENGTHS
    unstable_segment_health: frozenset[str] = UNSTABLE_SEGMENT_HEALTH


def workflow_rule_config_from_investigation(
    config: InvestigationWorkflowConfig,
) -> WorkflowRuleConfig:
    """Map severity YAML into engine WorkflowRuleConfig."""
    th = config.thresholds
    return WorkflowRuleConfig(
        contributor_concentration_pp=th.contributor_concentration_pp,
        strategy_nearby_days=th.strategy_nearby_days,
        default_strategy_name=th.default_strategy.name,
        default_strategy_deployment=th.default_strategy.deployment_date,
        trend_deterioration_directions=frozenset(th.trend_deterioration.directions),
        trend_deterioration_strengths=frozenset(th.trend_deterioration.strengths),
        unstable_segment_health=frozenset(th.unstable_segment_health),
    )


def load_workflow_rule_config(
    config_root: str | None = None,
) -> WorkflowRuleConfig:
    """Build rule thresholds from external YAML."""
    return workflow_rule_config_from_investigation(
        load_investigation_workflow_config(config_root)
    )


def load_investigation_workflow_config(
    config_root: str | None = None,
) -> InvestigationWorkflowConfig:
    """Load merged workflow_rules + skill_triggers + severity_thresholds."""
    ensure_workflow_config_path()
    from workflow_config.loaders.workflow_config_loader import get_default_workflow_config

    return get_default_workflow_config(config_root)


def strategy_deployment_nearby(
    analysis_date: date,
    deployment_date: date,
    *,
    window_days: int = STRATEGY_DEPLOYMENT_NEARBY_DAYS,
) -> bool:
    """True when analysis window overlaps post-deployment review period."""
    return abs((analysis_date - deployment_date).days) <= window_days
