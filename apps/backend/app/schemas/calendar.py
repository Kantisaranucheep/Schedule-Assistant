# schedule-assistant/apps/backend/app/schemas/calendar.py
"""Calendar Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CalendarBase(BaseModel):
    """Base schema for calendar data."""

    name: str
    timezone: str | None = None


class CalendarCreate(CalendarBase):
    """Schema for creating a calendar."""

    user_id: UUID


class CalendarRead(CalendarBase):
    """Schema for reading calendar data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
