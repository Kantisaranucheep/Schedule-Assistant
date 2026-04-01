"""Event schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EventBase(BaseModel):
    """Base event fields."""

    title: str = Field(..., max_length=255)
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    location: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = None
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")


class EventCreate(EventBase):
    """Create event request."""

    calendar_id: UUID


class EventUpdate(BaseModel):
    """Update event request."""

    title: Optional[str] = Field(default=None, max_length=255)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    location: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = None
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    status: Optional[str] = Field(default=None, pattern=r"^(confirmed|cancelled|tentative)$")


class EventResponse(EventBase):
    """Event response."""

    id: UUID
    calendar_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
