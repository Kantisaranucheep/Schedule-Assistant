"""Calendar schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CalendarBase(BaseModel):
    """Base calendar fields."""

    name: str = Field(default="My Calendar", max_length=255)
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")
    timezone: str = Field(default="Asia/Bangkok", max_length=50)


class CalendarCreate(CalendarBase):
    """Create calendar request."""

    user_id: UUID


class CalendarUpdate(BaseModel):
    """Update calendar request."""

    name: Optional[str] = Field(default=None, max_length=255)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    timezone: Optional[str] = Field(default=None, max_length=50)


class CalendarResponse(CalendarBase):
    """Calendar response."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
