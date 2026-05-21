"""Deterministic pattern detectors over persisted investigation findings."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import ClassVar
from uuid import uuid4

from sqlalchemy.orm import Session

from intelligence_memory.patterns.schemas.detected_pattern import DetectedPattern
from intelligence_memory.patterns.schemas.pattern_signal import PatternSignal
from intelligence_memory.repositories.finding_repository import (
    FindingRepository,
    FindingSearchFilters,
)
from intelligence_memory.schemas.stored_finding import StoredFinding

logger = logging.getLogger(__name__)

CONTRIBUTOR_FINDING_TYPE = "dimension_contribution"
SEGMENT_FINDING_TYPE = "segment_stability"
STRATEGY_FINDING_TYPE = "strategy_impact"
STRATEGY_DIMENSION = "strategy"

_SUMMARY_APPROVAL_RE = re.compile(r"approval[_\s-]*delta[_\s-]*pp\s*[:=]\s*([-\d.]+)", re.I)
_SUMMARY_VOLUME_RE = re.compile(r"volume[_\s-]*delta[_\s-]*pct\s*[:=]\s*([-\d.]+)", re.I)


@dataclass(frozen=True)
class DetectorConfig:
    """Shared thresholds for pattern detectors."""

    window_days: int = 30
    min_occurrences: int = 3
    top_n: int = 3
    segment_instability_delta_pp: float = -0.15
    approval_decline_pp: float = -1.0
    fpd7_improvement_pp: float = -0.3
    fpd7_worsening_pp: float = 0.3
    volume_loss_pct: float = -5.0
    tradeoff_risk_improvement_cap_pp: float = 0.5


def compute_confidence_score(
    *,
    occurrence_count: int,
    min_occurrences: int,
    consistent_direction_ratio: float,
    severity_magnitude: float,
    severity_cap: float,
    investigation_count: int,
) -> float:
    """Deterministic confidence in [0, 1] from frequency, consistency, severity, recurrence."""
    freq = min(1.0, occurrence_count / max(min_occurrences, 1))
    consistency = max(0.0, min(1.0, consistent_direction_ratio))
    severity = min(1.0, abs(severity_magnitude) / max(severity_cap, 1e-6))
    recurrence = min(1.0, investigation_count / max(min_occurrences, 1))
    return round(0.25 * freq + 0.25 * consistency + 0.25 * severity + 0.25 * recurrence, 4)


def _strategy_metrics(finding: StoredFinding) -> tuple[float | None, float | None, float | None]:
    """Return (fpd7_delta_pp, approval_delta_pp, volume_delta_pct) from row or summary."""
    fpd7 = finding.delta_pp
    approval = finding.approval_delta_pp
    volume = finding.volume_delta_pct
    if approval is None and finding.summary:
        match = _SUMMARY_APPROVAL_RE.search(finding.summary)
        if match:
            approval = float(match.group(1))
    if volume is None and finding.summary:
        match = _SUMMARY_VOLUME_RE.search(finding.summary)
        if match:
            volume = float(match.group(1))
    return fpd7, approval, volume


def _window_start(reference_date: date, window_days: int) -> datetime:
    start = reference_date - timedelta(days=window_days)
    return datetime.combine(start, time.min, tzinfo=timezone.utc)


def _top_contributors(findings: list[StoredFinding], *, top_n: int) -> list[StoredFinding]:
    ranked = sorted(
        findings,
        key=lambda f: abs(f.contribution_pp or 0.0),
        reverse=True,
    )
    return ranked[:top_n]


def _signals_to_pattern(
    *,
    pattern_type: str,
    key: str,
    signals: list[PatternSignal],
    summary: str,
    min_occurrences: int,
    severity_cap: float,
    dimension_name: str | None = None,
    dimension_value: str | None = None,
    metric_name: str | None = None,
) -> DetectedPattern | None:
    if len(signals) < min_occurrences:
        return None

    inv_ids = sorted({s.investigation_id for s in signals})
    finding_ids = sorted({fid for s in signals for fid in s.finding_ids})
    timestamps = [s.generated_at for s in signals]
    magnitudes = [s.severity_magnitude for s in signals]
    positive = sum(1 for m in magnitudes if m >= 0)
    negative = sum(1 for m in magnitudes if m < 0)
    dominant = max(positive, negative)
    consistency = dominant / len(magnitudes) if magnitudes else 0.0
    avg_severity = sum(abs(m) for m in magnitudes) / len(magnitudes) if magnitudes else 0.0

    confidence = compute_confidence_score(
        occurrence_count=len(signals),
        min_occurrences=min_occurrences,
        consistent_direction_ratio=consistency,
        severity_magnitude=avg_severity,
        severity_cap=severity_cap,
        investigation_count=len(inv_ids),
    )

    return DetectedPattern(
        pattern_id=f"{pattern_type}:{key}",
        pattern_type=pattern_type,
        pattern_summary=summary,
        supporting_findings=finding_ids,
        confidence_score=confidence,
        first_detected_at=min(timestamps),
        last_detected_at=max(timestamps),
        investigation_ids=inv_ids,
        dimension_name=dimension_name,
        dimension_value=dimension_value,
        metric_name=metric_name,
        occurrence_count=len(signals),
    )


class PatternDetector(ABC):
    """Base class for deterministic pattern detectors."""

    pattern_type: ClassVar[str]

    @abstractmethod
    def detect(
        self,
        session: Session,
        *,
        config: DetectorConfig | None = None,
        metric_name: str | None = None,
        reference_date: date | None = None,
    ) -> list[DetectedPattern]:
        """Run detection and return zero or more patterns."""


class RecurringContributorDetector(PatternDetector):
    """Partner/dimension value repeatedly in top-N contributors across investigations."""

    pattern_type = "recurring_contributor"

    def detect(
        self,
        session: Session,
        *,
        config: DetectorConfig | None = None,
        metric_name: str | None = None,
        reference_date: date | None = None,
    ) -> list[DetectedPattern]:
        cfg = config or DetectorConfig()
        ref = reference_date or datetime.now(timezone.utc).date()
        repo = FindingRepository(session)
        rows = repo.search(
            FindingSearchFilters(
                metric_name=metric_name,
                finding_type=CONTRIBUTOR_FINDING_TYPE,
                date_from=_window_start(ref, cfg.window_days),
                limit=5000,
            )
        )
        if not rows:
            return []

        by_investigation: dict[str, list[StoredFinding]] = defaultdict(list)
        for row in rows:
            if row.dimension_name and row.dimension_value:
                by_investigation[row.investigation_id].append(row)

        contributor_hits: dict[tuple[str, str, str | None], list[PatternSignal]] = defaultdict(
            list
        )
        for inv_id, inv_findings in by_investigation.items():
            for finding in _top_contributors(inv_findings, top_n=cfg.top_n):
                key = (
                    finding.dimension_name or "",
                    finding.dimension_value or "",
                    finding.metric_name,
                )
                contributor_hits[key].append(
                    PatternSignal(
                        signal_type="top_contributor",
                        investigation_id=inv_id,
                        finding_ids=[finding.finding_id],
                        dimension_name=finding.dimension_name,
                        dimension_value=finding.dimension_value,
                        metric_name=finding.metric_name,
                        severity_magnitude=abs(finding.contribution_pp or 0.0),
                        generated_at=finding.generated_at,
                    )
                )

        patterns: list[DetectedPattern] = []
        for (dim_name, dim_value, met), signals in sorted(
            contributor_hits.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        ):
            pattern = _signals_to_pattern(
                pattern_type=self.pattern_type,
                key=f"{dim_name}:{dim_value}:{met or ''}",
                signals=signals,
                summary=(
                    f"{dim_value} appeared in top {cfg.top_n} contributors "
                    f"{len(signals)} times in the last {cfg.window_days} days"
                ),
                min_occurrences=cfg.min_occurrences,
                severity_cap=1.0,
                dimension_name=dim_name,
                dimension_value=dim_value,
                metric_name=met,
            )
            if pattern:
                patterns.append(pattern)
        return patterns


class RecurringSegmentInstabilityDetector(PatternDetector):
    """Segment instability (negative delta_pp) recurring across investigations."""

    pattern_type = "recurring_segment_instability"

    def detect(
        self,
        session: Session,
        *,
        config: DetectorConfig | None = None,
        metric_name: str | None = None,
        reference_date: date | None = None,
    ) -> list[DetectedPattern]:
        cfg = config or DetectorConfig()
        ref = reference_date or datetime.now(timezone.utc).date()
        repo = FindingRepository(session)
        rows = repo.search(
            FindingSearchFilters(
                metric_name=metric_name,
                finding_type=SEGMENT_FINDING_TYPE,
                date_from=_window_start(ref, cfg.window_days),
                limit=5000,
            )
        )

        unstable: dict[tuple[str, str, str | None], list[PatternSignal]] = defaultdict(list)
        for finding in rows:
            if finding.dimension_name is None or finding.dimension_value is None:
                continue
            delta = finding.delta_pp
            if delta is None or delta > cfg.segment_instability_delta_pp:
                continue
            key = (finding.dimension_name, finding.dimension_value, finding.metric_name)
            unstable[key].append(
                PatternSignal(
                    signal_type="segment_unstable",
                    investigation_id=finding.investigation_id,
                    finding_ids=[finding.finding_id],
                    dimension_name=finding.dimension_name,
                    dimension_value=finding.dimension_value,
                    metric_name=finding.metric_name,
                    severity_magnitude=delta,
                    generated_at=finding.generated_at,
                )
            )

        patterns: list[DetectedPattern] = []
        for (dim_name, dim_value, met), signals in sorted(
            unstable.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        ):
            pattern = _signals_to_pattern(
                pattern_type=self.pattern_type,
                key=f"{dim_name}:{dim_value}:{met or ''}",
                signals=signals,
                summary=(
                    f"Segment {dim_name}={dim_value} showed instability "
                    f"in {len(signals)} investigations (last {cfg.window_days} days)"
                ),
                min_occurrences=cfg.min_occurrences,
                severity_cap=0.5,
                dimension_name=dim_name,
                dimension_value=dim_value,
                metric_name=met,
            )
            if pattern:
                patterns.append(pattern)
        return patterns


class StrategySideEffectDetector(PatternDetector):
    """Approval decline accompanied by FPD improvement — recurring strategy side effect."""

    pattern_type = "strategy_side_effect"

    def detect(
        self,
        session: Session,
        *,
        config: DetectorConfig | None = None,
        metric_name: str | None = None,
        reference_date: date | None = None,
    ) -> list[DetectedPattern]:
        cfg = config or DetectorConfig()
        ref = reference_date or datetime.now(timezone.utc).date()
        repo = FindingRepository(session)
        rows = repo.search(
            FindingSearchFilters(
                finding_type=STRATEGY_FINDING_TYPE,
                date_from=_window_start(ref, cfg.window_days),
                limit=5000,
            )
        )

        by_strategy: dict[str, list[PatternSignal]] = defaultdict(list)
        for finding in rows:
            fpd7, approval, _volume = _strategy_metrics(finding)
            if approval is None or fpd7 is None:
                continue
            if approval > cfg.approval_decline_pp or fpd7 > cfg.fpd7_improvement_pp:
                continue
            strategy = finding.dimension_value or "unknown"
            by_strategy[strategy].append(
                PatternSignal(
                    signal_type="approval_down_fpd_improved",
                    investigation_id=finding.investigation_id,
                    finding_ids=[finding.finding_id],
                    dimension_name=STRATEGY_DIMENSION,
                    dimension_value=strategy,
                    metric_name=finding.metric_name,
                    severity_magnitude=abs(approval) + abs(fpd7),
                    generated_at=finding.generated_at,
                    metadata={
                        "approval_delta_pp": approval,
                        "fpd7_delta_pp": fpd7,
                    },
                )
            )

        patterns: list[DetectedPattern] = []
        for strategy, signals in sorted(by_strategy.items(), key=lambda x: len(x[1]), reverse=True):
            pattern = _signals_to_pattern(
                pattern_type=self.pattern_type,
                key=strategy,
                signals=signals,
                summary=(
                    f"Strategy {strategy}: approval decline typically accompanies FPD improvement "
                    f"({len(signals)} occurrences)"
                ),
                min_occurrences=cfg.min_occurrences,
                severity_cap=5.0,
                dimension_name=STRATEGY_DIMENSION,
                dimension_value=strategy,
            )
            if pattern:
                patterns.append(pattern)
        return patterns


class ApprovalRiskShiftDetector(PatternDetector):
    """Recurring approval decline with risk metric worsening (FPD deterioration)."""

    pattern_type = "approval_risk_shift"

    def detect(
        self,
        session: Session,
        *,
        config: DetectorConfig | None = None,
        metric_name: str | None = None,
        reference_date: date | None = None,
    ) -> list[DetectedPattern]:
        cfg = config or DetectorConfig()
        ref = reference_date or datetime.now(timezone.utc).date()
        repo = FindingRepository(session)
        rows = repo.search(
            FindingSearchFilters(
                finding_type=STRATEGY_FINDING_TYPE,
                date_from=_window_start(ref, cfg.window_days),
                limit=5000,
            )
        )

        by_strategy: dict[str, list[PatternSignal]] = defaultdict(list)
        for finding in rows:
            fpd7, approval, _volume = _strategy_metrics(finding)
            if approval is None or fpd7 is None:
                continue
            if approval > cfg.approval_decline_pp or fpd7 < cfg.fpd7_worsening_pp:
                continue
            strategy = finding.dimension_value or "unknown"
            by_strategy[strategy].append(
                PatternSignal(
                    signal_type="approval_down_risk_up",
                    investigation_id=finding.investigation_id,
                    finding_ids=[finding.finding_id],
                    dimension_name=STRATEGY_DIMENSION,
                    dimension_value=strategy,
                    severity_magnitude=abs(approval) + abs(fpd7),
                    generated_at=finding.generated_at,
                    metadata={
                        "approval_delta_pp": approval,
                        "fpd7_delta_pp": fpd7,
                    },
                )
            )

        patterns: list[DetectedPattern] = []
        for strategy, signals in sorted(by_strategy.items(), key=lambda x: len(x[1]), reverse=True):
            pattern = _signals_to_pattern(
                pattern_type=self.pattern_type,
                key=strategy,
                signals=signals,
                summary=(
                    f"Strategy {strategy}: recurring approval decline with risk deterioration "
                    f"({len(signals)} occurrences)"
                ),
                min_occurrences=cfg.min_occurrences,
                severity_cap=6.0,
                dimension_name=STRATEGY_DIMENSION,
                dimension_value=strategy,
            )
            if pattern:
                patterns.append(pattern)
        return patterns


class VolumeRiskTradeoffDetector(PatternDetector):
    """Volume loss exceeds risk improvement — over-tightening strategy pattern."""

    pattern_type = "volume_risk_tradeoff"

    def detect(
        self,
        session: Session,
        *,
        config: DetectorConfig | None = None,
        metric_name: str | None = None,
        reference_date: date | None = None,
    ) -> list[DetectedPattern]:
        cfg = config or DetectorConfig()
        ref = reference_date or datetime.now(timezone.utc).date()
        repo = FindingRepository(session)
        rows = repo.search(
            FindingSearchFilters(
                finding_type=STRATEGY_FINDING_TYPE,
                date_from=_window_start(ref, cfg.window_days),
                limit=5000,
            )
        )

        by_strategy: dict[str, list[PatternSignal]] = defaultdict(list)
        for finding in rows:
            fpd7, _approval, volume = _strategy_metrics(finding)
            if volume is None or fpd7 is None:
                continue
            if volume > cfg.volume_loss_pct:
                continue
            risk_gain_pp = max(0.0, -fpd7)
            volume_loss_pct = abs(volume)
            if volume_loss_pct <= risk_gain_pp:
                continue
            if risk_gain_pp <= cfg.tradeoff_risk_improvement_cap_pp and volume_loss_pct < abs(
                cfg.volume_loss_pct
            ):
                continue

            strategy = finding.dimension_value or "unknown"
            by_strategy[strategy].append(
                PatternSignal(
                    signal_type="volume_loss_exceeds_risk_gain",
                    investigation_id=finding.investigation_id,
                    finding_ids=[finding.finding_id],
                    dimension_name=STRATEGY_DIMENSION,
                    dimension_value=strategy,
                    severity_magnitude=volume_loss_pct,
                    generated_at=finding.generated_at,
                    metadata={
                        "volume_delta_pct": volume,
                        "fpd7_delta_pp": fpd7,
                        "risk_gain_pp": risk_gain_pp,
                    },
                )
            )

        patterns: list[DetectedPattern] = []
        for strategy, signals in sorted(by_strategy.items(), key=lambda x: len(x[1]), reverse=True):
            pattern = _signals_to_pattern(
                pattern_type=self.pattern_type,
                key=strategy,
                signals=signals,
                summary=(
                    f"Strategy {strategy}: volume loss exceeds risk improvement "
                    f"(possible over-tightening, {len(signals)} occurrences)"
                ),
                min_occurrences=cfg.min_occurrences,
                severity_cap=15.0,
                dimension_name=STRATEGY_DIMENSION,
                dimension_value=strategy,
            )
            if pattern:
                patterns.append(pattern)
        return patterns


def new_pattern_id() -> str:
    """Generate a unique pattern id when not derived from entity key."""
    return str(uuid4())
