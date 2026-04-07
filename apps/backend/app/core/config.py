"""Application configuration from environment variables."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.timezone import get_system_timezone_name


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

    # Defaults - uses detected system timezone instead of hardcoded value
    default_timezone: str = get_system_timezone_name()
    default_working_hours_start: str = "09:00"
    default_working_hours_end: str = "18:00"

    # Ollama LLM Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # SMTP Email Configuration for Notifications
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_from_name: str = "Schedule Assistant"
    
    # Notification Settings
    notification_check_interval_seconds: int = 60  # How often to check for notifications


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
