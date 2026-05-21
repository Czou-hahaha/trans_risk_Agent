"""Deterministic findings → narrative report (no raw-data LLM)."""

from __future__ import annotations

from pathlib import Path

from workflow.investigation_context import InvestigationContext
from report.markdown_renderer import render_investigation_markdown
from report.report_sections import InvestigationReportSections, ReportSection


class InvestigationReportBuilder:
    """Build structured sections, executive summary, and markdown file."""

    def __init__(self, reports_dir: Path | None = None) -> None:
        engine_root = Path(__file__).resolve().parents[1]
        self._reports_dir = reports_dir or (engine_root / "reports")

    def build(self, ctx: InvestigationContext) -> tuple[InvestigationReportSections, str, Path]:
        sections = self.build_sections(ctx)
        executive = self.generate_executive_summary(ctx, sections)
        ctx.executive_summary = executive
        sections.executive_summary = ReportSection(
            title="Executive Summary",
            body=executive,
        )
        markdown = render_investigation_markdown(
            metric_name=ctx.metric_name,
            investigation_id=ctx.investigation_id,
            analysis_date=ctx.analysis_date.isoformat(),
            sections=sections,
        )
        path = self.write_markdown(ctx.investigation_id, markdown)
        ctx.generated_report_path = str(path)
        return sections, markdown, path

    def build_sections(self, ctx: InvestigationContext) -> InvestigationReportSections:
        return InvestigationReportSections(
            executive_summary=ReportSection(
                title="Executive Summary",
                body="",
            ),
            trend_analysis=self._trend_section(ctx),
            key_contributors=self._contributors_section(ctx),
            segment_stability=self._segment_section(ctx),
            strategy_impact=self._strategy_section(ctx),
            risk_recommendations=self._recommendations_section(ctx),
        )

    def generate_executive_summary(
        self,
        ctx: InvestigationContext,
        sections: InvestigationReportSections | None = None,
    ) -> str:
        parts: list[str] = []
        monitor = ctx.monitor_finding
        metric = ctx.metric_name.upper()

        if monitor:
            direction = "deterioration" if monitor.delta_pp > 0 else "improvement"
            parts.append(
                f"Portfolio {metric} showed {abs(monitor.delta_pp):.2f}pp {direction} "
                f"(current {monitor.current_value * 100:.2f}% vs prior "
                f"{monitor.previous_value * 100:.2f}%)."
            )
        elif not parts:
            parts.append(f"Portfolio {metric} remained within normal monitoring bounds.")

        contributors = ctx.contribution_findings
        if contributors:
            top = contributors[0]
            parts.append(
                f"The move was primarily driven by {top.dimension_name}={top.dimension_value} "
                f"(contribution {top.contribution_pp:+.2f}pp)."
            )

        trend = ctx.trend_finding
        if trend and trend.trend_direction == "upward":
            parts.append(
                f"Recent trend analysis indicates sustained upward pressure "
                f"({trend.rolling_change_pp:+.2f}pp rolling change)."
            )

        unstable = ctx.top_unstable_segments[:2]
        if unstable:
            labels = ", ".join(
                f"{s.dimension_name}={s.dimension_value}" for s in unstable
            )
            parts.append(
                f"Unstable segments include {labels}, with elevated volatility "
                f"or consecutive deterioration."
            )

        strategy = ctx.strategy_finding
        if strategy:
            eff = strategy.strategy_effectiveness.replace("_", " ")
            parts.append(
                f"Nearby strategy {strategy.strategy_name} deployment shows "
                f"FPD7 {strategy.fpd7_delta_pp:+.2f}pp and approval "
                f"{strategy.approval_delta_pp:+.2f}pp ({eff})."
            )

        conclusion = ctx.investigation_conclusion
        if conclusion and conclusion.recommended_actions:
            parts.append(
                f"Recommended focus: {conclusion.recommended_actions[0]}"
            )

        if not parts:
            return (
                f"No material risk signals detected for {metric} "
                f"as of {ctx.analysis_date.isoformat()}."
            )
        return " ".join(parts)

    def write_markdown(self, investigation_id: str, markdown: str) -> Path:
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        path = self._reports_dir / f"investigation_{investigation_id}.md"
        path.write_text(markdown, encoding="utf-8")
        return path

    def _trend_section(self, ctx: InvestigationContext) -> ReportSection:
        trend = ctx.trend_finding
        if not trend:
            return ReportSection(
                title="Trend Analysis",
                body="Trend analysis was not executed or yielded no finding.",
            )
        return ReportSection(
            title="Trend Analysis",
            body=trend.summary,
            bullets=[
                f"Direction: {trend.trend_direction}",
                f"Strength: {trend.trend_strength}",
                f"Rolling change: {trend.rolling_change_pp:+.2f}pp",
                f"Consecutive up periods: {trend.consecutive_up_periods}",
            ],
        )

    def _contributors_section(self, ctx: InvestigationContext) -> ReportSection:
        contribs = ctx.contribution_findings
        if not contribs:
            return ReportSection(
                title="Key Contributors",
                body="No dimension contribution analysis was recorded.",
            )
        bullets = [
            f"#{c.rank} {c.dimension_name}={c.dimension_value}: "
            f"contribution {c.contribution_pp:+.2f}pp, delta {c.delta_pp:+.2f}pp"
            for c in contribs[:5]
        ]
        return ReportSection(
            title="Key Contributors",
            body=f"Top {min(5, len(contribs))} contributors ranked by absolute contribution.",
            bullets=bullets,
        )

    def _segment_section(self, ctx: InvestigationContext) -> ReportSection:
        segments = ctx.top_unstable_segments
        if not segments:
            return ReportSection(
                title="Segment Stability",
                body="Segment stability review did not flag material instability.",
            )
        bullets = [
            f"{s.dimension_value}: health={s.segment_health}, "
            f"stability={s.stability_score:.2f}, volatility={s.volatility_level}"
            for s in segments[:5]
        ]
        return ReportSection(
            title="Segment Stability",
            body="Segments with elevated instability or deterioration:",
            bullets=bullets,
        )

    def _strategy_section(self, ctx: InvestigationContext) -> ReportSection:
        finding = ctx.strategy_finding
        if not finding:
            return ReportSection(
                title="Strategy Impact",
                body="No nearby strategy deployment impact analysis was available.",
            )
        return ReportSection(
            title="Strategy Impact",
            body=finding.summary,
            bullets=[
                f"Strategy: {finding.strategy_name}",
                f"FPD7 delta: {finding.fpd7_delta_pp:+.2f}pp",
                f"Approval delta: {finding.approval_delta_pp:+.2f}pp",
                f"Volume delta: {finding.volume_delta_pct:+.1f}%",
                f"Effectiveness: {finding.strategy_effectiveness}",
                f"Risk reduction efficiency: {finding.risk_reduction_efficiency:.2f}",
            ],
        )

    def _recommendations_section(self, ctx: InvestigationContext) -> ReportSection:
        conclusion = ctx.investigation_conclusion
        if conclusion:
            return ReportSection(
                title="Risk Recommendations",
                body=conclusion.risk_hypothesis or "See recommended actions below.",
                bullets=list(conclusion.recommended_actions) or [
                    "Continue monitoring portfolio-level metrics.",
                ],
            )
        bullets = ["Review top contributor segment policies."]
        if ctx.trend_finding and ctx.trend_finding.trend_direction == "upward":
            bullets.append("Investigate sustained upward trend drivers.")
        if ctx.top_unstable_segments:
            bullets.append("Stabilize or restrict high-volatility partner segments.")
        return ReportSection(
            title="Risk Recommendations",
            body="Deterministic recommendations from investigation findings.",
            bullets=bullets,
        )
