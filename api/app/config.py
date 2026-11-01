"""Runtime configuration. Secrets are read only from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration shared by the API, graph, and provider adapters."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Reverse Engineer a Business Failure"
    environment: str = Field(default="development", validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"))
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/reverse_failure.db"
    redis_url: str = "redis://redis:6379/0"
    cors_origins: str = "http://localhost:3000"
    demo_mode: str = "live"  # live | record | replay
    fixtures_dir: Path = Path("../fixtures")
    sec_user_agent: str = "ReverseBusinessFailure contact@example.com"
    sec_base_url: str = "https://data.sec.gov"
    sec_ticker_directory_url: str = "https://www.sec.gov/files/company_tickers.json"
    exa_api_key: str | None = None
    cerebras_api_key: str | None = None
    cerebras_model: str = "gpt-oss-120b"
    openai_api_key: str | None = None
    sarvam_api_key: str | None = None
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_chat_model: str = "sarvam-105b"
    sarvam_stt_model: str = "saaras:v4"
    # Sarvam's current low-latency Bulbul v4 model identifier.
    sarvam_tts_model: str = "bulbul:v4-flash"
    sarvam_tts_speaker: str | None = None
    max_voice_seconds: int = Field(default=30, ge=1, le=30)
    max_voice_bytes: int = Field(default=2_500_000, ge=100_000)
    max_assistant_context_chars: int = Field(default=24_000, ge=2_000)

    @property
    def fixture_path(self) -> Path:
        return self.fixtures_dir.resolve()

    @property
    def is_replay(self) -> bool:
        return self.demo_mode.lower() == "replay"

    @property
    def is_recording(self) -> bool:
        return self.demo_mode.lower() == "record"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
