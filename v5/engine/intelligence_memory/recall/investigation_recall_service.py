"""Cross-investigation historical recall — deterministic intelligence layer."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date

from sqlalchemy.orm import Session, sessionmaker

from intelligence_memory.recall.historical_lookup_engine import (
    DateRange,
    HistoricalLookupEngine,
)
from intelligence_memory.recall.recurring_contributor_engine import RecurringContributorEngine
from intelligence_memory.recall.schemas.recall_result import MatchedInvestigation, RecallResult
from intelligence_memory.repositories.finding_repository import FindingRepository
from intelligence_memory.repositories.investigation_repository import InvestigationRepository
from intelligence_memory.schemas.investigation_snapshot import InvestigationSnapshot
from intelligence_memory.schemas.stored_finding import StoredFinding
from intelligence_memory.storage.session import SessionLocal, init_db

logger = logging.getLogger(__name__)

STRATEGY_DIMENSION = "strategy"
STRATEGY_FINDING_TYPE = "strategy_impact"
SEGMENT_FINDING_TYPE = "segment_stability"
CONTRIBUTOR_FINDING_TYPE = "dimension_contribution"

_SIMILARITY_WEIGHTS = {
    "shared_contributor": 1.0,
    "shared_strategy": 2.0,
    "shared_deterioration_metric": 1.0,
    "shared_unstable_segment": 1.0,
}


class InvestigationRecallService:
    """Historical recall API over persisted findings and investigation snapshots."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        auto_init: bool = True,
    ) -> None:
        self._session_factory = session_factory or SessionLocal
        if auto_init:
            init_db()

    @contextmanager
    def _session_scope(self) -> Generator[Session, None, None]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_recurring_contributors(
        self,
        *,
        window_days: int = 30,
        min_occurrences: int = 3,
        top_n: int = 3,
        metric_name: str | None = None,
    ) -> RecallResult:
        with self._session_scope() as session:
            patterns = RecurringContributorEngine(session).detect(
                window_days=window_days,
                min_occurrences=min_occurrences,
                top_n=top_n,
                metric_name=metric_name,
            )
        frequency = {
            f"{p.dimension_name}:{p.dimension_value}": p.occurrence_count
            for p in patterns
        }
        matched = [
            MatchedInvestigation(
                investigation_id=inv_id,
                metric_name=p.metric_name or metric_name or "",
                similarity_score=0.0,
                match_reasons=[f"recurring_contributor:{p.dimension_value}"],
            )
            for p in patterns
            for inv_id in p.investigation_ids
        ]
        return RecallResult(
            recurring_patterns=patterns,
            historical_frequency=frequency,
            matched_investigations=_dedupe_matched(matched),
        )

    def get_historical_dimension_deterioration(
        self,
        dimension_name: str,
        dimension_value: str,
        *,
        metric_name: str | None = None,
        date_range: DateRange | None = None,
    ) -> RecallResult:
        with self._session_scope() as session:
            engine = HistoricalLookupEngine(session)
            findings = engine.lookup_deterioration(
                dimension_name=dimension_name,
                dimension_value=dimension_value,
                metric_name=metric_name,
                date_range=date_range,
            )
            freq = engine.frequency_by_investigation(findings)
            snapshots = InvestigationRepository(session)
            matched: list[MatchedInvestigation] = []
            for inv_id, count in freq.items():
                snap = snapshots.get_snapshot(inv_id)
                matched.append(
                    MatchedInvestigation(
                        investigation_id=inv_id,
                        metric_name=snap.metric_name if snap else (metric_name or ""),
                        analysis_date=snap.analysis_date if snap else None,
                        similarity_score=0.0,
                        match_reasons=[f"deterioration_count:{count}"],
                    )
                )
        return RecallResult(
            findings=findings,
            matched_investigations=matched,
            historical_frequency=freq,
        )

    def get_strategy_history(
        self,
        *,
        strategy_name: str | None = None,
        metric_name: str | None = None,
        date_range: DateRange | None = None,
        limit: int = 200,
    ) -> RecallResult:
        with self._session_scope() as session:
            engine = HistoricalLookupEngine(session)
            findings = engine.lookup(
                metric_name=metric_name,
                dimension_name=STRATEGY_DIMENSION,
                dimension_value=strategy_name,
                finding_type=STRATEGY_FINDING_TYPE,
                date_range=date_range,
                limit=limit,
            )
            freq = engine.frequency_by_investigation(findings)
            inv_repo = InvestigationRepository(session)
            matched = _findings_to_matched(findings, inv_repo, reason_prefix="strategy")
        strategy_freq: dict[str, int] = defaultdict(int)
        for f in findings:
            if f.dimension_value:
                strategy_freq[f.dimension_value] += 1
        return RecallResult(
            findings=findings,
            matched_investigations=matched,
            historical_frequency=dict(strategy_freq) or freq,
        )

    def get_recent_investigations(
        self,
        *,
        limit: int = 20,
        metric_name: str | None = None,
    ) -> RecallResult:
        with self._session_scope() as session:
            recent = InvestigationRepository(session).list_recent(
                limit=limit, metric_name=metric_name
            )
        return RecallResult(recent_investigations=recent)

    def find_similar_investigations(
        self,
        investigation_id: str,
        *,
        limit: int = 10,
        min_score: float = 1.0,
    ) -> RecallResult:
        with self._session_scope() as session:
            finding_repo = FindingRepository(session)
            inv_repo = InvestigationRepository(session)
            target_findings = finding_repo.list_by_investigation(investigation_id)
            if not target_findings:
                logger.warning("No findings for investigation_id=%s", investigation_id)
                return RecallResult(similarity_score=0.0)

            target_sig = _InvestigationSignature.from_findings(target_findings)
            all_investigations = inv_repo.list_all(limit=500)
            scores: list[tuple[str, float, list[str]]] = []

            for snap in all_investigations:
                if snap.investigation_id == investigation_id:
                    continue
                other_findings = finding_repo.list_by_investigation(snap.investigation_id)
                if not other_findings:
                    continue
                other_sig = _InvestigationSignature.from_findings(other_findings)
                score, reasons = _compute_similarity(target_sig, other_sig)
                if score >= min_score:
                    scores.append((snap.investigation_id, score, reasons))

            scores.sort(key=lambda x: x[1], reverse=True)
            top = scores[:limit]
            matched = [
                MatchedInvestigation(
                    investigation_id=inv_id,
                    metric_name=next(
                        (s.metric_name for s in all_investigations if s.investigation_id == inv_id),
                        "",
                    ),
                    analysis_date=next(
                        (s.analysis_date for s in all_investigations if s.investigation_id == inv_id),
                        None,
                    ),
                    similarity_score=score,
                    match_reasons=reasons,
                )
                for inv_id, score, reasons in top
            ]
            max_score = top[0][1] if top else 0.0

        return RecallResult(
            matched_investigations=matched,
            similarity_score=max_score,
        )


class _InvestigationSignature:
    """Deterministic feature set for similarity comparison."""

    def __init__(
        self,
        contributors: set[tuple[str, str]],
        strategies: set[str],
        deterioration_metrics: set[str],
        unstable_segments: set[tuple[str, str]],
    ) -> None:
        self.contributors = contributors
        self.strategies = strategies
        self.deterioration_metrics = deterioration_metrics
        self.unstable_segments = unstable_segments

    @classmethod
    def from_findings(cls, findings: list[StoredFinding]) -> _InvestigationSignature:
        contributors: set[tuple[str, str]] = set()
        strategies: set[str] = set()
        deterioration_metrics: set[str] = set()
        unstable_segments: set[tuple[str, str]] = set()

        for f in findings:
            if f.finding_type == CONTRIBUTOR_FINDING_TYPE and f.dimension_name and f.dimension_value:
                contributors.add((f.dimension_name, f.dimension_value))
            if f.finding_type == STRATEGY_FINDING_TYPE and f.dimension_value:
                strategies.add(f.dimension_value)
            if f.finding_type == SEGMENT_FINDING_TYPE and f.dimension_name and f.dimension_value:
                unstable_segments.add((f.dimension_name, f.dimension_value))
            if f.metric_name and (f.delta_pp is not None and f.delta_pp < 0):
                deterioration_metrics.add(f.metric_name)
            elif "deterioration" in (f.summary or "").lower():
                deterioration_metrics.add(f.metric_name)

        return cls(
            contributors=contributors,
            strategies=strategies,
            deterioration_metrics=deterioration_metrics,
            unstable_segments=unstable_segments,
        )


def _compute_similarity(
    target: _InvestigationSignature,
    other: _InvestigationSignature,
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    shared_contrib = target.contributors & other.contributors
    if shared_contrib:
        w = _SIMILARITY_WEIGHTS["shared_contributor"]
        score += len(shared_contrib) * w
        for dim_name, dim_value in sorted(shared_contrib):
            reasons.append(f"shared_contributor:{dim_name}={dim_value}")

    shared_strat = target.strategies & other.strategies
    if shared_strat:
        w = _SIMILARITY_WEIGHTS["shared_strategy"]
        score += len(shared_strat) * w
        for name in sorted(shared_strat):
            reasons.append(f"shared_strategy:{name}")

    shared_met = target.deterioration_metrics & other.deterioration_metrics
    if shared_met:
        w = _SIMILARITY_WEIGHTS["shared_deterioration_metric"]
        score += len(shared_met) * w
        for m in sorted(shared_met):
            reasons.append(f"shared_metric_deterioration:{m}")

    shared_seg = target.unstable_segments & other.unstable_segments
    if shared_seg:
        w = _SIMILARITY_WEIGHTS["shared_unstable_segment"]
        score += len(shared_seg) * w
        for dim_name, dim_value in sorted(shared_seg):
            reasons.append(f"shared_unstable_segment:{dim_name}={dim_value}")

    return score, reasons


def _findings_to_matched(
    findings: list[StoredFinding],
    inv_repo: InvestigationRepository,
    *,
    reason_prefix: str,
) -> list[MatchedInvestigation]:
    seen: set[str] = set()
    matched: list[MatchedInvestigation] = []
    for f in findings:
        if f.investigation_id in seen:
            continue
        seen.add(f.investigation_id)
        snap = inv_repo.get_snapshot(f.investigation_id)
        matched.append(
            MatchedInvestigation(
                investigation_id=f.investigation_id,
                metric_name=f.metric_name,
                analysis_date=snap.analysis_date if snap else None,
                match_reasons=[reason_prefix],
            )
        )
    return matched


def _dedupe_matched(items: list[MatchedInvestigation]) -> list[MatchedInvestigation]:
    by_id: dict[str, MatchedInvestigation] = {}
    for item in items:
        existing = by_id.get(item.investigation_id)
        if existing is None:
            by_id[item.investigation_id] = item
        else:
            existing.match_reasons = list(
                set(existing.match_reasons) | set(item.match_reasons)
            )
    return list(by_id.values())
