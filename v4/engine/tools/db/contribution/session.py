"""Database engine and session factory."""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from tools.db.contribution.base import Base

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.dimension_contribution_database_url, pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def ensure_database_exists() -> None:
    """Create risk_dimension_contribution database if it does not exist."""
    url = make_url(settings.dimension_contribution_database_url)
    db_name = url.database
    if not db_name:
        raise ValueError("Database name missing in DIMENSION_CONTRIBUTION_DATABASE_URL")

    admin_url = url.set(database="postgres")
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


def init_db() -> None:
    """Create all tables."""
    from tools.db.contribution.models.metric_breakdowns import MetricBreakdown  # noqa: F401

    Base.metadata.create_all(bind=engine)


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
