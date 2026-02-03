# schedule-assistant/apps/backend/app/schemas/settings.py
"""User settings Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SettingsBase(BaseModel):
    """Base schema for user settings data."""

    timezone: str = "Asia/Bangkok"
    default_duration_min: int = 60
    buffer_min: int = 10
    preferences: Dict[str, Any] = {}


class SettingsUpdate(BaseModel):
    """Schema for updating user settings."""

    timezone: str | None = None
    default_duration_min: int | None = None
    buffer_min: int | None = None
    preferences: Dict[str, Any] | None = None


class SettingsRead(SettingsBase):
    """Schema for reading user settings data."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    created_at: datetime
    updated_at: datetime
