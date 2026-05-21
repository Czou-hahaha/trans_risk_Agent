"""Risk intelligence database session factory."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from intelligence_memory.storage.persistence_models import IntelligenceBase

logger = logging.getLogger(__name__)

engine = create_engine(settings.intelligence_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def ensure_database_exists(url: str | None = None) -> None:
    """Create risk_intelligence database if missing."""
    target = make_url(url or settings.intelligence_database_url)
    db_name = target.database
    if not db_name:
        raise ValueError("Database name missing in INTELLIGENCE_DATABASE_URL")

    admin_url = target.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info("Created database %s", db_name)
    finally:
        admin_engine.dispose()


def init_db(bind: Engine | None = None) -> None:
    """Ensure DB exists and create intelligence tables."""
    ensure_database_exists()
    IntelligenceBase.metadata.create_all(bind=bind or engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
