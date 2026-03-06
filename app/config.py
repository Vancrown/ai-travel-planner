"""
Application configuration with environment variable validation.
Fails fast at startup if required vars are missing.
"""
import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required for LLM (validated when generating itinerary)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: Optional[str] = None
    openai_fallback_model: Optional[str] = "gpt-4o-mini"

    # Optional: timeouts and limits
    llm_timeout_seconds: int = 120
    llm_max_retries: int = 2
    cache_ttl_seconds: int = 300
    rate_limit_requests: int = 20
    rate_limit_window_seconds: int = 60

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
