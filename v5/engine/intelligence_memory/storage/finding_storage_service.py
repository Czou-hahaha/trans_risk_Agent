"""High-level API for structured findings persistence."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from contextlib import contextmanager
from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from intelligence_memory.repositories.finding_repository import FindingRepository
from intelligence_memory.repositories.investigation_repository import InvestigationRepository
from intelligence_memory.schemas.investigation_snapshot import InvestigationSnapshot
from intelligence_memory.schemas.stored_finding import StoredFinding
from intelligence_memory.storage.finding_mapper import finding_dict_to_stored
from intelligence_memory.storage.session import SessionLocal, init_db

logger = logging.getLogger(__name__)


class FindingStorageService:
    """Persist and query investigation findings across runs."""

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

    def store_finding(self, finding: StoredFinding) -> StoredFinding:
        with self._session_scope() as session:
            return FindingRepository(session).insert(finding)

    def store_findings_batch(self, findings: list[StoredFinding]) -> list[StoredFinding]:
        if not findings:
            return []
        with self._session_scope() as session:
            return FindingRepository(session).insert_batch(findings)

    def get_findings_by_metric(
        self, metric_name: str, *, limit: int = 100
    ) -> list[StoredFinding]:
        with self._session_scope() as session:
            return FindingRepository(session).list_by_metric(metric_name, limit=limit)

    def get_findings_by_dimension(
        self,
        dimension_name: str,
        dimension_value: str,
        *,
        limit: int = 100,
    ) -> list[StoredFinding]:
        with self._session_scope() as session:
            return FindingRepository(session).list_by_dimension(
                dimension_name, dimension_value, limit=limit
            )

    def get_findings_by_investigation(self, investigation_id: str) -> list[StoredFinding]:
        with self._session_scope() as session:
            return FindingRepository(session).list_by_investigation(investigation_id)

    def persist_investigation_findings(
        self,
        investigation_id: str,
        metric_name: str,
        findings: list[dict[str, Any]],
        *,
        analysis_date: Any = None,
        workflow_status: str = "completed",
        needs_investigation: bool | None = None,
        trigger_reason: str | None = None,
    ) -> list[StoredFinding]:
        """Map runtime finding dicts, persist findings + investigation snapshot."""
        stored = [
            finding_dict_to_stored(
                f, investigation_id=investigation_id, metric_name=metric_name
            )
            for f in findings
        ]
        if stored:
            self.store_findings_batch(stored)

        snapshot = InvestigationSnapshot(
            investigation_id=investigation_id,
            metric_name=metric_name,
            analysis_date=analysis_date or stored[0].generated_at.date(),
            workflow_status=workflow_status,
            findings_count=len(stored),
            needs_investigation=needs_investigation,
            trigger_reason=trigger_reason,
            generated_at=datetime.now(timezone.utc),
        )
        with self._session_scope() as session:
            InvestigationRepository(session).upsert_snapshot(snapshot)

        logger.info(
            "Persisted findings investigation_id=%s count=%d",
            investigation_id,
            len(stored),
        )
        return stored
