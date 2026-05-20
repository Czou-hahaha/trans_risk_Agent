"""Human-readable step output previews for timeline UI."""

from __future__ import annotations

from models.contribution import ContributionFinding
from models.conclusion import InvestigationConclusion
from models.metric_monitor import MetricMonitorFinding


def monitor_preview(finding: MetricMonitorFinding) -> str:
    sign = "+" if finding.delta_pp >= 0 else ""
    return (
        f"detected {finding.metric_name.upper()} "
        f"{finding.direction.value} {sign}{finding.delta_pp:.2f}pp"
    )


def contribution_preview(findings: list[ContributionFinding]) -> str:
    if not findings:
        return "no significant contributors found"
    top = findings[0]
    sign = "+" if top.contribution_pp >= 0 else ""
    return (
        f"{top.dimension_value} contributed {sign}{top.contribution_pp:.2f}pp "
        f"({top.dimension_name})"
    )


def summary_preview(conclusion: InvestigationConclusion) -> str:
    driver = conclusion.primary_driver or "portfolio"
    return f"generated investigation conclusion — primary driver: {driver}"
