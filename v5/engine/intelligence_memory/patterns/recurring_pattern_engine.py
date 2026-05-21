"""Orchestrates cross-investigation recurring pattern detection."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date

from sqlalchemy.orm import Session, sessionmaker

from intelligence_memory.patterns.pattern_detector import DetectorConfig
from intelligence_memory.patterns.pattern_registry import PatternRegistry
from intelligence_memory.patterns.schemas.detected_pattern import DetectedPattern
from intelligence_memory.storage.session import SessionLocal, init_db

logger = logging.getLogger(__name__)


class RecurringPatternEngine:
    """Run all registered detectors and return historical investigation intelligence."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        registry: PatternRegistry | None = None,
        auto_init: bool = True,
    ) -> None:
        self._session_factory = session_factory or SessionLocal
        self._registry = registry or PatternRegistry()
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

    def detect_all(
        self,
        *,
        config: DetectorConfig | None = None,
        metric_name: str | None = None,
        reference_date: date | None = None,
        pattern_types: list[str] | None = None,
        min_confidence: float = 0.0,
    ) -> list[DetectedPattern]:
        """Run detectors and return patterns sorted by confidence (desc)."""
        cfg = config or DetectorConfig()
        detectors = self._registry.all_detectors()
        if pattern_types:
            allowed = set(pattern_types)
            detectors = [d for d in detectors if d.pattern_type in allowed]

        all_patterns: list[DetectedPattern] = []
        with self._session_scope() as session:
            for detector in detectors:
                try:
                    found = detector.detect(
                        session,
                        config=cfg,
                        metric_name=metric_name,
                        reference_date=reference_date,
                    )
                    all_patterns.extend(found)
                except Exception:
                    logger.exception(
                        "Pattern detector failed type=%s", detector.pattern_type
                    )

        filtered = [p for p in all_patterns if p.confidence_score >= min_confidence]
        filtered.sort(key=lambda p: p.confidence_score, reverse=True)
        return filtered

    def detect_by_type(
        self,
        pattern_type: str,
        *,
        config: DetectorConfig | None = None,
        metric_name: str | None = None,
        reference_date: date | None = None,
    ) -> list[DetectedPattern]:
        """Run a single detector by pattern_type."""
        return self.detect_all(
            config=config,
            metric_name=metric_name,
            reference_date=reference_date,
            pattern_types=[pattern_type],
        )

    def summarize_intelligence(
        self,
        patterns: list[DetectedPattern],
    ) -> dict[str, object]:
        """Lightweight aggregate for dashboards or APIs."""
        by_type: dict[str, int] = {}
        for p in patterns:
            by_type[p.pattern_type] = by_type.get(p.pattern_type, 0) + 1
        return {
            "pattern_count": len(patterns),
            "patterns_by_type": by_type,
            "top_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "pattern_type": p.pattern_type,
                    "pattern_summary": p.pattern_summary,
                    "confidence_score": p.confidence_score,
                    "occurrence_count": p.occurrence_count,
                }
                for p in patterns[:10]
            ],
        }
