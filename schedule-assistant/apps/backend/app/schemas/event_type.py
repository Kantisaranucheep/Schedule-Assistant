# schedule-assistant/apps/backend/app/schemas/event_type.py
"""Event type Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EventTypeBase(BaseModel):
    """Base schema for event type data."""

    name: str
    color: str | None = None
    default_duration_min: int | None = None


class EventTypeCreate(EventTypeBase):
    """Schema for creating an event type."""

    user_id: UUID


class EventTypeRead(EventTypeBase):
    """Schema for reading event type data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
