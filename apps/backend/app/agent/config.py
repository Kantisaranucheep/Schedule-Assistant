# apps/backend/app/agent/config.py
"""Agent configuration settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Settings for the agent module."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout: int = 60

    # Gemini settings
    agent_enable_gemini: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-pro"

    # Prolog settings
    prolog_mode: Literal["subprocess", "service"] = "subprocess"
    prolog_service_url: str = "http://localhost:8081"
    prolog_kb_path: str = "../../prolog"  # Relative to backend app

    # Agent behavior
    agent_default_confidence_threshold: float = 0.7
    agent_max_retries: int = 2


@lru_cache
def get_agent_settings() -> AgentSettings:
    """Get cached agent settings instance."""
    return AgentSettings()
