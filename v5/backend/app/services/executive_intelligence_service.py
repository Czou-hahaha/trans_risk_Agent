"""Aggregate cross-investigation intelligence for the executive dashboard."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from intelligence_memory.patterns import RecurringPatternEngine
from intelligence_memory.patterns.pattern_detector import DetectorConfig
from intelligence_memory.patterns.schemas.detected_pattern import DetectedPattern
from intelligence_memory.recall.recurring_contributor_engine import RecurringContributorEngine
from intelligence_memory.repositories.investigation_repository import InvestigationRepository
from intelligence_memory.storage.session import SessionLocal, init_db

from app.schemas.executive import (
    ExecutiveIntelligenceOut,
    IntelligenceItem,
    PatternIntelligence,
    TrendIntelligence,
    WeeklyHighlight,
    WeeklyRiskSummary,
)

logger = logging.getLogger(__name__)

WEEKLY_WINDOW_DAYS = 7
PATTERN_WINDOW_DAYS = 30


def _pattern_to_item(p: DetectedPattern) -> IntelligenceItem:
    title = p.dimension_value or p.pattern_type.replace("_", " ").title()
    if p.dimension_name and p.dimension_value:
        title = f"{p.dimension_name}={p.dimension_value}"
    return IntelligenceItem(
        id=p.pattern_id,
        title=title,
        summary=p.pattern_summary,
        metric_name=p.metric_name,
        dimension_name=p.dimension_name,
        dimension_value=p.dimension_value,
        occurrence_count=p.occurrence_count,
        confidence_score=p.confidence_score,
        investigation_ids=p.investigation_ids,
        pattern_type=p.pattern_type,
    )


def _contributor_to_item(
    *,
    pattern_id: str,
    dimension_name: str,
    dimension_value: str,
    metric_name: str | None,
    occurrence_count: int,
    summary: str,
    investigation_ids: list[str],
) -> IntelligenceItem:
    confidence = min(1.0, occurrence_count / 5.0)
    return IntelligenceItem(
        id=pattern_id,
        title=f"{dimension_name}={dimension_value}",
        summary=summary,
        metric_name=metric_name,
        dimension_name=dimension_name,
        dimension_value=dimension_value,
        occurrence_count=occurrence_count,
        confidence_score=round(confidence, 2),
        investigation_ids=investigation_ids,
        pattern_type="recurring_contributor",
    )


def _build_weekly_summary(
    *,
    reference: datetime,
    weekly_patterns: list[DetectedPattern],
    investigation_count: int,
) -> WeeklyRiskSummary:
    highlights: list[WeeklyHighlight] = []
    by_type: dict[str, list[DetectedPattern]] = defaultdict(list)
    for p in weekly_patterns:
        by_type[p.pattern_type].append(p)

    type_labels = {
        "recurring_contributor": ("贡献因子", "high"),
        "recurring_segment_instability": ("不稳定分群", "high"),
        "strategy_side_effect": ("策略副作用", "medium"),
        "approval_risk_shift": ("审批风险", "high"),
        "volume_risk_tradeoff": ("体量-风险权衡", "medium"),
    }

    for pattern_type, label_sev in type_labels.items():
        group = sorted(
            by_type.get(pattern_type, []),
            key=lambda x: x.confidence_score,
            reverse=True,
        )
        if not group:
            continue
        top = group[0]
        label, severity = label_sev
        highlights.append(
            WeeklyHighlight(
                category=label,
                headline=top.pattern_summary[:120],
                detail=(
                    f"置信度 {top.confidence_score:.0%} · "
                    f"出现 {top.occurrence_count} 次 · "
                    f"关联 {len(top.investigation_ids)} 次调查"
                ),
                severity=severity,
            )
        )

    if not highlights:
        headline = "过去 7 天暂无显著跨调查风险模式；完成更多调查后将自动生成周报。"
    elif len(highlights) == 1:
        headline = f"过去 7 天最重要变化：{highlights[0].headline}"
    else:
        headline = (
            f"过去 7 天检测到 {len(weekly_patterns)} 条跨调查信号，"
            f"涵盖 {len(by_type)} 类风险模式"
        )

    return WeeklyRiskSummary(
        period_label="过去 7 天",
        generated_at=reference,
        headline=headline,
        highlights=highlights[:6],
        investigation_count=investigation_count,
        pattern_count=len(weekly_patterns),
    )


def build_executive_intelligence(
    *,
    weekly_window_days: int = WEEKLY_WINDOW_DAYS,
    pattern_window_days: int = PATTERN_WINDOW_DAYS,
) -> ExecutiveIntelligenceOut:
    """Build executive dashboard payload from intelligence memory."""
    now = datetime.now(timezone.utc)
    ref_date = now.date()
    weekly_cfg = DetectorConfig(window_days=weekly_window_days, min_occurrences=2)
    pattern_cfg = DetectorConfig(window_days=pattern_window_days, min_occurrences=3)

    try:
        init_db()
    except Exception:
        logger.exception("Intelligence DB init failed")

    weekly_patterns: list[DetectedPattern] = []
    all_patterns: list[DetectedPattern] = []
    contributors: list[IntelligenceItem] = []
    investigation_count = 0
    data_available = False
    message: str | None = None

    try:
        engine = RecurringPatternEngine(auto_init=False)
        weekly_patterns = engine.detect_all(config=weekly_cfg, reference_date=ref_date)
        all_patterns = engine.detect_all(config=pattern_cfg, reference_date=ref_date)
        data_available = True
    except Exception as exc:
        logger.exception("Pattern detection failed")
        message = f"Pattern engine unavailable: {exc}"

    try:
        with SessionLocal() as session:
            contrib_engine = RecurringContributorEngine(session)
            raw_contributors = contrib_engine.detect(
                window_days=pattern_window_days,
                min_occurrences=2,
                reference_date=ref_date,
            )
            for i, p in enumerate(raw_contributors[:8]):
                contributors.append(
                    _contributor_to_item(
                        pattern_id=f"contrib-{i}-{p.dimension_value}",
                        dimension_name=p.dimension_name or "dimension",
                        dimension_value=p.dimension_value or "",
                        metric_name=p.metric_name,
                        occurrence_count=p.occurrence_count,
                        summary=p.summary,
                        investigation_ids=p.investigation_ids,
                    )
                )

            inv_repo = InvestigationRepository(session)
            window_start = ref_date - timedelta(days=weekly_window_days)
            recent = inv_repo.list_in_date_range(
                date_from=window_start,
                date_to=ref_date,
                limit=100,
            )
            investigation_count = len(recent)
            data_available = data_available or bool(recent)
    except Exception as exc:
        logger.exception("Recall / contributor detection failed")
        if message:
            message = f"{message}; recall failed: {exc}"
        else:
            message = f"Intelligence recall unavailable: {exc}"

    pattern_items = [_pattern_to_item(p) for p in all_patterns]

    top_contributors = contributors or [
        item
        for item in pattern_items
        if item.pattern_type == "recurring_contributor"
    ][:8]

    unstable_segments = [
        item for item in pattern_items if item.pattern_type == "recurring_segment_instability"
    ][:8]

    high_risk_strategies = [
        item
        for item in pattern_items
        if item.pattern_type
        in ("strategy_side_effect", "approval_risk_shift", "volume_risk_tradeoff")
    ]
    high_risk_strategies.sort(key=lambda x: x.confidence_score, reverse=True)
    high_risk_strategies = high_risk_strategies[:8]

    deterioration = [
        item
        for item in pattern_items
        if item.pattern_type in ("recurring_segment_instability", "approval_risk_shift")
        or "deterioration" in item.summary.lower()
        or "恶化" in item.summary
    ]
    deterioration = deterioration[:8]

    weekly_items = [_pattern_to_item(p) for p in weekly_patterns]
    weekly_summary = _build_weekly_summary(
        reference=now,
        weekly_patterns=weekly_patterns,
        investigation_count=investigation_count,
    )

    trend = TrendIntelligence(
        risk_trend_shifts=[
            i
            for i in weekly_items + pattern_items
            if i.pattern_type == "recurring_segment_instability"
            or "risk" in (i.summary or "").lower()
        ][:6],
        approval_trend_shifts=[
            i for i in pattern_items if i.pattern_type == "approval_risk_shift"
        ][:6],
        volume_risk_tradeoffs=[
            i for i in pattern_items if i.pattern_type == "volume_risk_tradeoff"
        ][:6],
    )

    cross_signals = sorted(
        pattern_items,
        key=lambda x: (x.confidence_score, x.occurrence_count),
        reverse=True,
    )[:10]

    pattern_intel = PatternIntelligence(
        recurring_patterns=pattern_items[:10],
        historical_recurrence=sorted(
            pattern_items,
            key=lambda x: x.occurrence_count,
            reverse=True,
        )[:10],
        cross_investigation_signals=cross_signals,
    )

    if not data_available and not message:
        message = (
            "Intelligence memory 暂无数据。请先完成调查 workflow，"
            "findings 将自动写入 risk_intelligence 库。"
        )

    return ExecutiveIntelligenceOut(
        generated_at=now,
        window_days=weekly_window_days,
        data_available=data_available,
        message=message,
        top_recurring_contributors=top_contributors,
        most_unstable_segments=unstable_segments,
        highest_risk_strategies=high_risk_strategies,
        recurring_deterioration_patterns=deterioration,
        weekly_summary=weekly_summary,
        trend_intelligence=trend,
        pattern_intelligence=pattern_intel,
    )
