"""Investigation persistence database session."""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import Base

logger = logging.getLogger(__name__)

engine = create_engine(settings.investigation_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def ensure_database_exists() -> None:
    """Create risk_investigation database if missing (local Postgres without docker init)."""
    url = make_url(settings.investigation_database_url)
    db_name = url.database
    if not db_name:
        raise ValueError("Database name missing in INVESTIGATION_DATABASE_URL")

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
    ensure_database_exists()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
