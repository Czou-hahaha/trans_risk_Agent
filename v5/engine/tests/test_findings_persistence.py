"""Tests for Risk Intelligence Storage Layer — findings persistence."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from intelligence_memory.schemas.stored_finding import StoredFinding
from intelligence_memory.storage.finding_storage_service import FindingStorageService
from intelligence_memory.storage.persistence_models import IntelligenceBase


@pytest.fixture
def storage() -> FindingStorageService:
    engine = create_engine("sqlite:///:memory:")
    IntelligenceBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return FindingStorageService(session_factory=factory, auto_init=False)


def _sample_finding(
    *,
    finding_id: str = "f-001",
    investigation_id: str = "inv-001",
    metric_name: str = "fpd7",
    finding_type: str = "dimension_contribution",
    dimension_name: str = "channel",
    dimension_value: str = "paid_search",
    contribution_pp: float = 0.42,
    delta_pp: float = 0.15,
) -> StoredFinding:
    return StoredFinding(
        finding_id=finding_id,
        investigation_id=investigation_id,
        metric_name=metric_name,
        finding_type=finding_type,
        dimension_name=dimension_name,
        dimension_value=dimension_value,
        summary="channel paid_search contributed +0.42pp",
        severity=None,
        contribution_pp=contribution_pp,
        delta_pp=delta_pp,
        generated_at=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc),
    )


class TestFindingsPersistence:
    def test_single_finding_persistence(self, storage: FindingStorageService) -> None:
        finding = _sample_finding()
        stored = storage.store_finding(finding)
        assert stored.finding_id == "f-001"

        rows = storage.get_findings_by_investigation("inv-001")
        assert len(rows) == 1
        assert rows[0].contribution_pp == pytest.approx(0.42)

    def test_batch_persistence(self, storage: FindingStorageService) -> None:
        batch = [
            _sample_finding(finding_id="f-001"),
            _sample_finding(
                finding_id="f-002",
                dimension_value="organic",
                contribution_pp=0.21,
            ),
        ]
        storage.store_findings_batch(batch)
        rows = storage.get_findings_by_investigation("inv-001")
        assert len(rows) == 2

    def test_retrieval_by_metric(self, storage: FindingStorageService) -> None:
        storage.store_findings_batch(
            [
                _sample_finding(finding_id="f-001", metric_name="fpd7"),
                _sample_finding(
                    finding_id="f-002",
                    investigation_id="inv-002",
                    metric_name="dpd30",
                    dimension_value="other",
                ),
            ]
        )
        rows = storage.get_findings_by_metric("fpd7")
        assert len(rows) == 1
        assert rows[0].metric_name == "fpd7"

    def test_retrieval_by_dimension(self, storage: FindingStorageService) -> None:
        storage.store_findings_batch(
            [
                _sample_finding(finding_id="f-001"),
                _sample_finding(
                    finding_id="f-002",
                    dimension_name="channel",
                    dimension_value="organic",
                ),
            ]
        )
        rows = storage.get_findings_by_dimension("channel", "paid_search")
        assert len(rows) == 1
        assert rows[0].dimension_value == "paid_search"

    def test_retrieval_by_investigation(self, storage: FindingStorageService) -> None:
        storage.store_findings_batch(
            [
                _sample_finding(finding_id="f-001", investigation_id="inv-a"),
                _sample_finding(finding_id="f-002", investigation_id="inv-b"),
            ]
        )
        rows = storage.get_findings_by_investigation("inv-a")
        assert len(rows) == 1
        assert rows[0].investigation_id == "inv-a"

    def test_persist_investigation_findings_from_dict(
        self, storage: FindingStorageService
    ) -> None:
        finding_dict = {
            "finding_id": "f-runtime",
            "finding_type": "dimension_contribution",
            "metric_name": "fpd7",
            "dimension_name": "channel",
            "dimension_value": "paid_search",
            "summary": "runtime contributor",
            "contribution_pp": 0.55,
            "delta_pp": 0.2,
            "generated_at": "2026-05-20T12:00:00+00:00",
        }
        stored = storage.persist_investigation_findings(
            "inv-runtime",
            "fpd7",
            [finding_dict],
            analysis_date=date(2026, 5, 20),
            workflow_status="completed",
            needs_investigation=True,
        )
        assert len(stored) == 1
        assert storage.get_findings_by_investigation("inv-runtime")[0].summary == (
            "runtime contributor"
        )
