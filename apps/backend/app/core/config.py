# schedule-assistant/apps/backend/app/core/config.py
"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/schedule_assistant"

    # Application
    app_name: str = "Schedule Assistant"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # CORS
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Default settings
    default_timezone: str = "Asia/Bangkok"
    default_working_hours_start: str = "09:00"
    default_working_hours_end: str = "18:00"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
