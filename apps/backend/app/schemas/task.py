"""Task schemas."""

from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """Base task fields."""

    title: str = Field(..., max_length=255)
    date: date
    location: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = None
    category_id: Optional[UUID] = None


class TaskCreate(TaskBase):
    """Create task request."""

    calendar_id: UUID


class TaskUpdate(BaseModel):
    """Update task request."""

    title: Optional[str] = Field(default=None, max_length=255)
    date: Optional[date] = None
    location: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = None
    category_id: Optional[UUID] = None
    status: Optional[str] = Field(default=None, pattern=r"^(pending|completed|cancelled)$")


class TaskResponse(TaskBase):
    """Task response."""

    id: UUID
    calendar_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
