"""Build report API payloads and markdown export."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.db.models import Investigation, InvestigationReport
from app.schemas.reports import ContributorRankingItem, ReportOut


def _parse_dt(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now()
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_report_out(inv: Investigation, report: InvestigationReport) -> ReportOut:
    data = report.report_json
    conclusion = data.get("investigation_conclusion") or {}
    contributors_raw = data.get("contribution_findings") or []
    ranking = [
        ContributorRankingItem(
            rank=c.get("rank", idx + 1),
            dimension_name=c.get("dimension_name", ""),
            dimension_value=c.get("dimension_value", ""),
            contribution_pp=float(c.get("contribution_pp", 0)),
            delta_pp=float(c.get("delta_pp", 0)),
        )
        for idx, c in enumerate(contributors_raw[:10])
    ]

    executive = data.get("executive_summary") or ""
    business = conclusion.get("business_summary") or executive or "No conclusion generated."
    hypothesis = conclusion.get("risk_hypothesis", "—")
    actions = conclusion.get("recommended_actions") or []

    markdown = data.get("generated_report_path")
    if markdown and isinstance(markdown, str):
        from pathlib import Path

        path = Path(markdown)
        if path.is_file():
            markdown_export = path.read_text(encoding="utf-8")
        else:
            markdown_export = _to_markdown(
                goal=inv.goal,
                metric_name=inv.metric_name,
                executive_summary=executive,
                business_summary=business,
                risk_hypothesis=hypothesis,
                recommended_actions=actions,
                ranking=ranking,
            )
    else:
        markdown_export = _to_markdown(
            goal=inv.goal,
            metric_name=inv.metric_name,
            executive_summary=executive,
            business_summary=business,
            risk_hypothesis=hypothesis,
            recommended_actions=actions,
            ranking=ranking,
        )

    return ReportOut(
        id=report.id,
        investigation_id=inv.id,
        goal=inv.goal,
        metric_name=inv.metric_name,
        workflow_status=data.get("workflow_status", inv.status),
        business_summary=business,
        risk_hypothesis=hypothesis,
        recommended_actions=actions,
        contributor_ranking=ranking,
        monitor_finding=data.get("monitor_finding"),
        executive_summary=executive,
        executed_skills=data.get("executed_skills") or [],
        timeline=data.get("timeline") or [],
        generated_at=_parse_dt(data.get("generated_at")),
        markdown_export=markdown_export,
    )


def _to_markdown(
    *,
    goal: str,
    metric_name: str,
    executive_summary: str,
    business_summary: str,
    risk_hypothesis: str,
    recommended_actions: list[str],
    ranking: list[ContributorRankingItem],
) -> str:
    lines = [
        f"# Investigation Report — {metric_name.upper()}",
        "",
        f"**Goal:** {goal}",
        "",
        "## Executive Summary",
        executive_summary or business_summary,
        "",
        "## Business Summary",
        business_summary,
        "",
        "## Risk Hypothesis",
        risk_hypothesis,
        "",
        "## Recommended Actions",
    ]
    lines.extend(f"- {a}" for a in recommended_actions)
    lines.extend(["", "## Contributor Ranking", ""])
    if ranking:
        lines.append("| Rank | Dimension | Value | Contribution (pp) | Delta (pp) |")
        lines.append("| --- | --- | --- | --- | --- |")
        for r in ranking:
            lines.append(
                f"| {r.rank} | {r.dimension_name} | {r.dimension_value} | "
                f"{r.contribution_pp:+.2f} | {r.delta_pp:+.2f} |"
            )
    else:
        lines.append("_No contributors recorded._")
    return "\n".join(lines)
