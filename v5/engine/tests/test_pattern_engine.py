"""Tests for Recurring Pattern Engine — cross-investigation pattern intelligence."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from intelligence_memory.patterns import RecurringPatternEngine
from intelligence_memory.patterns.pattern_detector import DetectorConfig
from intelligence_memory.schemas.stored_finding import StoredFinding
from intelligence_memory.storage.finding_storage_service import FindingStorageService
from intelligence_memory.storage.persistence_models import IntelligenceBase


@pytest.fixture
def pattern_stack() -> tuple[FindingStorageService, RecurringPatternEngine]:
    engine = create_engine("sqlite:///:memory:")
    IntelligenceBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    storage = FindingStorageService(session_factory=factory, auto_init=False)
    pattern_engine = RecurringPatternEngine(session_factory=factory, auto_init=False)
    return storage, pattern_engine


def _ts(day: int) -> datetime:
    return datetime(2026, 5, day, 12, 0, tzinfo=timezone.utc)


def _contributor_finding(
    *,
    finding_id: str,
    investigation_id: str,
    dimension_value: str,
    contribution_pp: float,
    generated_at: datetime,
) -> StoredFinding:
    return StoredFinding(
        finding_id=finding_id,
        investigation_id=investigation_id,
        metric_name="fpd7",
        finding_type="dimension_contribution",
        dimension_name="channel",
        dimension_value=dimension_value,
        summary=f"contributor {dimension_value}",
        contribution_pp=contribution_pp,
        generated_at=generated_at,
    )


def _strategy_finding(
    *,
    finding_id: str,
    investigation_id: str,
    strategy_name: str,
    approval_delta_pp: float,
    fpd7_delta_pp: float,
    volume_delta_pct: float,
    generated_at: datetime,
) -> StoredFinding:
    return StoredFinding(
        finding_id=finding_id,
        investigation_id=investigation_id,
        metric_name="strategy_impact",
        finding_type="strategy_impact",
        dimension_name="strategy",
        dimension_value=strategy_name,
        summary=(
            f"Strategy {strategy_name} impact "
            f"approval_delta_pp={approval_delta_pp} volume_delta_pct={volume_delta_pct}"
        ),
        delta_pp=fpd7_delta_pp,
        approval_delta_pp=approval_delta_pp,
        volume_delta_pct=volume_delta_pct,
        generated_at=generated_at,
    )


def _seed_recurring_partner(
    storage: FindingStorageService,
    *,
    partner: str = "partner_X",
    investigation_ids: list[str],
) -> None:
    for i, inv_id in enumerate(investigation_ids):
        day = 10 + i
        storage.store_findings_batch(
            [
                _contributor_finding(
                    finding_id=f"f-{inv_id}-top",
                    investigation_id=inv_id,
                    dimension_value=partner,
                    contribution_pp=0.9,
                    generated_at=_ts(day),
                ),
                _contributor_finding(
                    finding_id=f"f-{inv_id}-low",
                    investigation_id=inv_id,
                    dimension_value="other_channel",
                    contribution_pp=0.05,
                    generated_at=_ts(day),
                ),
            ]
        )


class TestRecurringContributors:
    def test_detects_partner_in_top_three_across_runs(
        self, pattern_stack: tuple[FindingStorageService, RecurringPatternEngine]
    ) -> None:
        storage, engine = pattern_stack
        _seed_recurring_partner(
            storage,
            investigation_ids=["inv-1", "inv-2", "inv-3"],
        )

        patterns = engine.detect_by_type(
            "recurring_contributor",
            config=DetectorConfig(min_occurrences=3, top_n=3),
            metric_name="fpd7",
        )

        assert len(patterns) >= 1
        pattern = next(p for p in patterns if p.dimension_value == "partner_X")
        assert pattern.pattern_type == "recurring_contributor"
        assert pattern.occurrence_count == 3
        assert set(pattern.investigation_ids) == {"inv-1", "inv-2", "inv-3"}
        assert pattern.confidence_score > 0.5
        assert len(pattern.supporting_findings) == 3


class TestStrategySideEffects:
    def test_approval_decline_with_fpd_improvement_recurring(
        self, pattern_stack: tuple[FindingStorageService, RecurringPatternEngine]
    ) -> None:
        storage, engine = pattern_stack
        for i, inv_id in enumerate(["inv-s1", "inv-s2", "inv-s3"]):
            storage.store_finding(
                _strategy_finding(
                    finding_id=f"side-{inv_id}",
                    investigation_id=inv_id,
                    strategy_name="RISK_003",
                    approval_delta_pp=-3.2,
                    fpd7_delta_pp=-1.1,
                    volume_delta_pct=-4.0,
                    generated_at=_ts(10 + i),
                )
            )

        patterns = engine.detect_by_type("strategy_side_effect", config=DetectorConfig(min_occurrences=3))

        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.pattern_type == "strategy_side_effect"
        assert pattern.dimension_value == "RISK_003"
        assert pattern.occurrence_count == 3
        assert "approval decline" in pattern.pattern_summary.lower()
        assert pattern.confidence_score > 0.4


class TestApprovalRiskShift:
    def test_approval_down_with_risk_worsening_recurring(
        self, pattern_stack: tuple[FindingStorageService, RecurringPatternEngine]
    ) -> None:
        storage, engine = pattern_stack
        for i, inv_id in enumerate(["inv-a1", "inv-a2", "inv-a3"]):
            storage.store_finding(
                _strategy_finding(
                    finding_id=f"shift-{inv_id}",
                    investigation_id=inv_id,
                    strategy_name="RISK_TIGHT",
                    approval_delta_pp=-2.5,
                    fpd7_delta_pp=0.6,
                    volume_delta_pct=-2.0,
                    generated_at=_ts(12 + i),
                )
            )

        patterns = engine.detect_by_type("approval_risk_shift", config=DetectorConfig(min_occurrences=3))

        assert len(patterns) == 1
        assert patterns[0].pattern_type == "approval_risk_shift"
        assert patterns[0].dimension_value == "RISK_TIGHT"
        assert patterns[0].occurrence_count == 3


class TestVolumeRiskTradeoff:
    def test_volume_loss_exceeds_risk_improvement(
        self, pattern_stack: tuple[FindingStorageService, RecurringPatternEngine]
    ) -> None:
        storage, engine = pattern_stack
        for i, inv_id in enumerate(["inv-v1", "inv-v2", "inv-v3"]):
            storage.store_finding(
                _strategy_finding(
                    finding_id=f"trade-{inv_id}",
                    investigation_id=inv_id,
                    strategy_name="RISK_OVER_TIGHT",
                    approval_delta_pp=-1.0,
                    fpd7_delta_pp=-0.2,
                    volume_delta_pct=-9.5,
                    generated_at=_ts(14 + i),
                )
            )

        patterns = engine.detect_by_type("volume_risk_tradeoff", config=DetectorConfig(min_occurrences=3))

        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.pattern_type == "volume_risk_tradeoff"
        assert "over-tightening" in pattern.pattern_summary.lower() or "volume loss" in pattern.pattern_summary.lower()
        assert pattern.occurrence_count == 3


class TestDetectAllAndSummary:
    def test_detect_all_returns_multiple_types_sorted_by_confidence(
        self, pattern_stack: tuple[FindingStorageService, RecurringPatternEngine]
    ) -> None:
        storage, engine = pattern_stack
        _seed_recurring_partner(storage, investigation_ids=["inv-1", "inv-2", "inv-3"])
        for i, inv_id in enumerate(["inv-s1", "inv-s2", "inv-s3"]):
            storage.store_finding(
                _strategy_finding(
                    finding_id=f"all-{inv_id}",
                    investigation_id=inv_id,
                    strategy_name="RISK_003",
                    approval_delta_pp=-3.0,
                    fpd7_delta_pp=-1.0,
                    volume_delta_pct=-10.0,
                    generated_at=_ts(20 + i),
                )
            )

        patterns = engine.detect_all(config=DetectorConfig(min_occurrences=3), metric_name="fpd7")
        types = {p.pattern_type for p in patterns}
        assert "recurring_contributor" in types
        assert len(patterns) >= 2
        scores = [p.confidence_score for p in patterns]
        assert scores == sorted(scores, reverse=True)

        summary = engine.summarize_intelligence(patterns)
        assert summary["pattern_count"] == len(patterns)
        assert summary["patterns_by_type"]
