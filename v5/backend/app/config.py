"""Backend settings — loads v5/.env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_V5_ROOT = Path(__file__).resolve().parents[2]


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_V5_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    investigation_database_url: str = (
        "postgresql+psycopg://risk:risk@localhost:5433/risk_investigation"
    )
    intelligence_database_url: str = (
        "postgresql+psycopg://risk:risk@localhost:5433/risk_intelligence"
    )
    backend_cors_origins: str = "http://localhost:8000"
    engine_root: Path = _V5_ROOT / "engine"


settings = BackendSettings()
