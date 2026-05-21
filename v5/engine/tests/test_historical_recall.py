"""Tests for Historical Recall — cross-investigation deterministic intelligence."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from intelligence_memory.recall import DateRange, InvestigationRecallService
from intelligence_memory.schemas.investigation_snapshot import InvestigationSnapshot
from intelligence_memory.schemas.stored_finding import StoredFinding
from intelligence_memory.storage.finding_storage_service import FindingStorageService
from intelligence_memory.storage.persistence_models import IntelligenceBase


@pytest.fixture
def recall_stack() -> tuple[FindingStorageService, InvestigationRecallService]:
    engine = create_engine("sqlite:///:memory:")
    IntelligenceBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    storage = FindingStorageService(session_factory=factory, auto_init=False)
    recall = InvestigationRecallService(session_factory=factory, auto_init=False)
    return storage, recall


def _ts(day: int) -> datetime:
    return datetime(2026, 5, day, 12, 0, tzinfo=timezone.utc)


def _contributor_finding(
    *,
    finding_id: str,
    investigation_id: str,
    dimension_value: str,
    contribution_pp: float,
    generated_at: datetime,
    metric_name: str = "fpd7",
) -> StoredFinding:
    return StoredFinding(
        finding_id=finding_id,
        investigation_id=investigation_id,
        metric_name=metric_name,
        finding_type="dimension_contribution",
        dimension_name="channel",
        dimension_value=dimension_value,
        summary=f"contributor {dimension_value}",
        contribution_pp=contribution_pp,
        delta_pp=0.1,
        generated_at=generated_at,
    )


def _snapshot(
    investigation_id: str,
    *,
    analysis_date: date | None = None,
    generated_at: datetime | None = None,
) -> InvestigationSnapshot:
    return InvestigationSnapshot(
        investigation_id=investigation_id,
        metric_name="fpd7",
        analysis_date=analysis_date or date(2026, 5, 20),
        workflow_status="completed",
        findings_count=1,
        generated_at=generated_at or _ts(20),
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
        storage.store_finding(
            StoredFinding(
                finding_id=f"f-{inv_id}-snap",
                investigation_id=inv_id,
                metric_name="fpd7",
                finding_type="metric_monitor",
                summary="monitor",
                generated_at=_ts(day),
            )
        )
        with storage._session_scope() as session:
            from intelligence_memory.repositories.investigation_repository import (
                InvestigationRepository,
            )

            InvestigationRepository(session).upsert_snapshot(
                _snapshot(inv_id, analysis_date=date(2026, 5, day), generated_at=_ts(day))
            )


class TestRecurringContributors:
    def test_detects_partner_in_top_three_across_runs(
        self, recall_stack: tuple[FindingStorageService, InvestigationRecallService]
    ) -> None:
        storage, recall = recall_stack
        _seed_recurring_partner(
            storage,
            investigation_ids=["inv-1", "inv-2", "inv-3"],
        )

        result = recall.get_recurring_contributors(
            window_days=30,
            min_occurrences=3,
            top_n=3,
            metric_name="fpd7",
        )

        assert len(result.recurring_patterns) >= 1
        pattern = next(
            p for p in result.recurring_patterns if p.dimension_value == "partner_X"
        )
        assert pattern.occurrence_count == 3
        assert set(pattern.investigation_ids) == {"inv-1", "inv-2", "inv-3"}
        assert result.historical_frequency.get("channel:partner_X") == 3

    def test_ignores_infrequent_contributor(
        self, recall_stack: tuple[FindingStorageService, InvestigationRecallService]
    ) -> None:
        storage, recall = recall_stack
        _seed_recurring_partner(storage, investigation_ids=["inv-1", "inv-2"])
        storage.store_findings_batch(
            [
                _contributor_finding(
                    finding_id="f-once",
                    investigation_id="inv-3",
                    dimension_value="rare_partner",
                    contribution_pp=0.8,
                    generated_at=_ts(15),
                )
            ]
        )

        result = recall.get_recurring_contributors(min_occurrences=3)
        values = {p.dimension_value for p in result.recurring_patterns}
        assert "rare_partner" not in values


class TestHistoricalLookup:
    def test_lookup_by_metric_and_finding_type(
        self, recall_stack: tuple[FindingStorageService, InvestigationRecallService]
    ) -> None:
        storage, recall = recall_stack
        storage.store_findings_batch(
            [
                _contributor_finding(
                    finding_id="f1",
                    investigation_id="inv-a",
                    dimension_value="paid",
                    contribution_pp=0.5,
                    generated_at=_ts(10),
                ),
                StoredFinding(
                    finding_id="f2",
                    investigation_id="inv-b",
                    metric_name="dpd30",
                    finding_type="dimension_contribution",
                    dimension_name="channel",
                    dimension_value="organic",
                    summary="other metric",
                    generated_at=_ts(11),
                ),
            ]
        )

        from intelligence_memory.recall.historical_lookup_engine import HistoricalLookupEngine

        with recall._session_scope() as session:
            rows = HistoricalLookupEngine(session).lookup(
                metric_name="fpd7",
                finding_type="dimension_contribution",
            )
        assert len(rows) == 1
        assert rows[0].dimension_value == "paid"


class TestDimensionDeterioration:
    def test_finds_negative_delta_history(
        self, recall_stack: tuple[FindingStorageService, InvestigationRecallService]
    ) -> None:
        storage, recall = recall_stack
        storage.store_findings_batch(
            [
                StoredFinding(
                    finding_id="d1",
                    investigation_id="inv-d1",
                    metric_name="fpd7",
                    finding_type="segment_stability",
                    dimension_name="channel",
                    dimension_value="partner_X",
                    summary="segment worsened",
                    delta_pp=-0.25,
                    generated_at=_ts(12),
                ),
                StoredFinding(
                    finding_id="d2",
                    investigation_id="inv-d2",
                    metric_name="fpd7",
                    finding_type="segment_stability",
                    dimension_name="channel",
                    dimension_value="partner_X",
                    summary="stable",
                    delta_pp=0.05,
                    generated_at=_ts(13),
                ),
            ]
        )

        result = recall.get_historical_dimension_deterioration("channel", "partner_X")
        assert len(result.findings) == 1
        assert result.findings[0].investigation_id == "inv-d1"
        assert result.historical_frequency.get("inv-d1") == 1


class TestStrategyHistory:
    def test_strategy_findings_grouped(
        self, recall_stack: tuple[FindingStorageService, InvestigationRecallService]
    ) -> None:
        storage, recall = recall_stack
        for inv_id, day in [("inv-s1", 10), ("inv-s2", 11)]:
            storage.store_findings_batch(
                [
                    StoredFinding(
                        finding_id=f"strat-{inv_id}",
                        investigation_id=inv_id,
                        metric_name="fpd7",
                        finding_type="strategy_impact",
                        dimension_name="strategy",
                        dimension_value="RISK_003",
                        summary="strategy impact",
                        delta_pp=-0.1,
                        generated_at=_ts(day),
                    )
                ]
            )

        result = recall.get_strategy_history(strategy_name="RISK_003")
        assert len(result.findings) == 2
        assert result.historical_frequency.get("RISK_003") == 2
        assert len(result.matched_investigations) == 2


class TestSimilarInvestigations:
    def test_shared_contributor_and_strategy_raise_score(
        self, recall_stack: tuple[FindingStorageService, InvestigationRecallService]
    ) -> None:
        storage, recall = recall_stack

        def _bundle(inv_id: str, *, partner: str, strategy: str, extra: str) -> list[StoredFinding]:
            return [
                _contributor_finding(
                    finding_id=f"{inv_id}-c",
                    investigation_id=inv_id,
                    dimension_value=partner,
                    contribution_pp=0.7,
                    generated_at=_ts(10),
                ),
                StoredFinding(
                    finding_id=f"{inv_id}-s",
                    investigation_id=inv_id,
                    metric_name="fpd7",
                    finding_type="strategy_impact",
                    dimension_name="strategy",
                    dimension_value=strategy,
                    summary="strat",
                    generated_at=_ts(10),
                ),
                StoredFinding(
                    finding_id=f"{inv_id}-seg",
                    investigation_id=inv_id,
                    metric_name="fpd7",
                    finding_type="segment_stability",
                    dimension_name="region",
                    dimension_value="west",
                    summary="unstable",
                    delta_pp=-0.2,
                    generated_at=_ts(10),
                ),
                StoredFinding(
                    finding_id=f"{inv_id}-x",
                    investigation_id=inv_id,
                    metric_name="fpd7",
                    finding_type="dimension_contribution",
                    dimension_name="channel",
                    dimension_value=extra,
                    summary="noise",
                    contribution_pp=0.01,
                    generated_at=_ts(10),
                ),
            ]

        storage.store_findings_batch(_bundle("inv-target", partner="partner_X", strategy="RISK_003", extra="noise_a"))
        storage.store_findings_batch(_bundle("inv-similar", partner="partner_X", strategy="RISK_003", extra="noise_b"))
        diff_bundle = _bundle("inv-diff", partner="other", strategy="RISK_999", extra="noise_c")
        diff_bundle[2] = StoredFinding(
            finding_id="inv-diff-seg",
            investigation_id="inv-diff",
            metric_name="fpd7",
            finding_type="segment_stability",
            dimension_name="region",
            dimension_value="east",
            summary="other region",
            delta_pp=0.1,
            generated_at=_ts(10),
        )
        storage.store_findings_batch(diff_bundle)

        for inv_id in ("inv-target", "inv-similar", "inv-diff"):
            with storage._session_scope() as session:
                from intelligence_memory.repositories.investigation_repository import (
                    InvestigationRepository,
                )

                InvestigationRepository(session).upsert_snapshot(_snapshot(inv_id))

        result = recall.find_similar_investigations("inv-target", min_score=3.0)
        assert result.similarity_score is not None
        assert result.similarity_score >= 4.0
        ids = [m.investigation_id for m in result.matched_investigations]
        assert "inv-similar" in ids
        assert "inv-diff" not in ids
        top = next(m for m in result.matched_investigations if m.investigation_id == "inv-similar")
        assert any("shared_contributor" in r for r in top.match_reasons)
        assert any("shared_strategy" in r for r in top.match_reasons)


class TestRecentInvestigations:
    def test_lists_snapshots_newest_first(
        self, recall_stack: tuple[FindingStorageService, InvestigationRecallService]
    ) -> None:
        storage, recall = recall_stack
        with storage._session_scope() as session:
            from intelligence_memory.repositories.investigation_repository import (
                InvestigationRepository,
            )

            repo = InvestigationRepository(session)
            repo.upsert_snapshot(
                _snapshot("inv-old", generated_at=_ts(5))
            )
            repo.upsert_snapshot(
                _snapshot("inv-new", generated_at=_ts(25))
            )

        result = recall.get_recent_investigations(limit=5)
        assert len(result.recent_investigations) == 2
        assert result.recent_investigations[0].investigation_id == "inv-new"
