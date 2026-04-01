"""Application configuration from environment variables."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Schedule Assistant"
    debug: bool = False
    secret_key: str = "dev-secret-change-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/schedule_assistant"

    # CORS
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Defaults
    default_timezone: str = "Asia/Bangkok"
    default_working_hours_start: str = "09:00"
    default_working_hours_end: str = "18:00"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
