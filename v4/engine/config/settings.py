"""Unified application settings — single .env at v4 root."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_V4_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_V4_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    metric_monitor_database_url: str = (
        "postgresql+psycopg://risk:risk@localhost:5433/risk_metric_monitor"
    )
    dimension_contribution_database_url: str = (
        "postgresql+psycopg://risk:risk@localhost:5433/risk_dimension_contribution"
    )

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    use_llm: bool = True

    anomaly_delta_pp_threshold: float = 0.3


settings = Settings()
