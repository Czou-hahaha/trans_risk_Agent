"""Structured report section payloads (deterministic)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReportSection:
    title: str
    body: str
    bullets: list[str] = field(default_factory=list)


@dataclass
class InvestigationReportSections:
    executive_summary: ReportSection
    trend_analysis: ReportSection
    key_contributors: ReportSection
    segment_stability: ReportSection
    strategy_impact: ReportSection
    risk_recommendations: ReportSection
