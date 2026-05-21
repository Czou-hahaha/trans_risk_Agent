"""Render investigation report sections to Markdown."""

from __future__ import annotations

from report.report_sections import InvestigationReportSections


def render_investigation_markdown(
    *,
    metric_name: str,
    investigation_id: str,
    analysis_date: str,
    sections: InvestigationReportSections,
) -> str:
    lines = [
        f"# Risk Investigation Report — {metric_name.upper()}",
        "",
        f"**Investigation ID:** `{investigation_id}`  ",
        f"**Analysis Date:** {analysis_date}",
        "",
        f"## {sections.executive_summary.title}",
        sections.executive_summary.body,
        "",
        f"## {sections.trend_analysis.title}",
        sections.trend_analysis.body,
    ]
    lines.extend(_bullets(sections.trend_analysis.bullets))
    lines.extend(
        [
            "",
            f"## {sections.key_contributors.title}",
            sections.key_contributors.body,
        ]
    )
    lines.extend(_bullets(sections.key_contributors.bullets))
    lines.extend(
        [
            "",
            f"## {sections.segment_stability.title}",
            sections.segment_stability.body,
        ]
    )
    lines.extend(_bullets(sections.segment_stability.bullets))
    lines.extend(
        [
            "",
            f"## {sections.strategy_impact.title}",
            sections.strategy_impact.body,
        ]
    )
    lines.extend(_bullets(sections.strategy_impact.bullets))
    lines.extend(
        [
            "",
            f"## {sections.risk_recommendations.title}",
            sections.risk_recommendations.body,
        ]
    )
    lines.extend(_bullets(sections.risk_recommendations.bullets))
    return "\n".join(lines)


def _bullets(items: list[str]) -> list[str]:
    if not items:
        return ["", "_No items._"]
    out = [""]
    out.extend(f"- {b}" for b in items)
    return out
