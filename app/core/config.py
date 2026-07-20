"""
Centralized application configuration.

All environment variables are loaded once here via pydantic-settings and
exposed as a single `settings` singleton. Every other module should import
`settings` from here instead of reading os.environ directly.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "AI ASO Platform"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = "sqlite:///./data/db/aso_platform.db"

    # --- Agent Runtime ---
    # "mock" (default, works offline) or "openfang_zeroclaw" (ZeroClaw HTTP gateway)
    agent_runtime: str = "mock"
    openfang_zeroclaw_api_key: str = ""
    openfang_zeroclaw_base_url: str = ""

    # --- Orchestration ---
    # "direct" = CoordinatorAgent Python pipeline (default, no LLM required)
    # "crewai" = Module 12 Crew wrapping the same agents as tools (needs LLM key)
    orchestration_mode: str = "direct"

    # --- LLM Provider ---
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # --- Data sources ---
    app_store_country: str = "us"
    google_play_country: str = "us"
    request_timeout_seconds: int = 15
    max_retries: int = 3
    retry_backoff_seconds: int = 2

    # --- Scheduler ---
    daily_report_hour: int = 6
    weekly_report_day: str = "mon"
    weekly_report_hour: int = 7

    # --- Reports ---
    reports_output_dir: str = "./data/reports"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so .env is parsed only once per process."""
    return Settings()


settings = get_settings()
