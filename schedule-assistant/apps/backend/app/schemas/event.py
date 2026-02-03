# schedule-assistant/apps/backend/app/schemas/event.py
"""Event Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class EventBase(BaseModel):
    """Base schema for event data."""

    title: str
    description: str | None = None
    location: str | None = None
    start_at: datetime
    end_at: datetime
    status: Literal["confirmed", "tentative", "cancelled"] = "confirmed"
    created_by: Literal["user", "agent"] = "user"

    @field_validator("end_at")
    @classmethod
    def validate_end_after_start(cls, v: datetime, info) -> datetime:
        """Ensure end_at is after start_at."""
        if "start_at" in info.data and v <= info.data["start_at"]:
            raise ValueError("end_at must be after start_at")
        return v


class EventCreate(EventBase):
    """Schema for creating an event."""

    calendar_id: UUID
    type_id: UUID | None = None


class EventUpdate(BaseModel):
    """Schema for updating an event."""

    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: Literal["confirmed", "tentative", "cancelled"] | None = None
    type_id: UUID | None = None


class EventRead(EventBase):
    """Schema for reading event data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    calendar_id: UUID
    type_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
