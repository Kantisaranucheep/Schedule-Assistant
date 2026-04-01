"""User settings schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserSettingsBase(BaseModel):
    """Base settings fields."""

    working_hours_start: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    working_hours_end: str = Field(default="18:00", pattern=r"^\d{2}:\d{2}$")
    buffer_minutes: int = Field(default=10, ge=0, le=120)


class UserSettingsCreate(UserSettingsBase):
    """Create settings request."""

    user_id: UUID


class UserSettingsUpdate(BaseModel):
    """Update settings request."""

    working_hours_start: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    working_hours_end: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    buffer_minutes: Optional[int] = Field(default=None, ge=0, le=120)


class UserSettingsResponse(UserSettingsBase):
    """Settings response."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
