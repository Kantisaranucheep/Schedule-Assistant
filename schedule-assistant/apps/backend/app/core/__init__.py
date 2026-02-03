# schedule-assistant/apps/backend/app/core/__init__.py
"""Core module containing configuration and database setup."""

from app.core.config import Settings, get_settings
from app.core.db import Base, get_db

__all__ = ["Settings", "get_settings", "Base", "get_db"]
