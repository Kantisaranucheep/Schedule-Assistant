# schedule-assistant/apps/backend/app/schemas/user.py
"""User Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    """Base schema for user data."""

    name: str | None = None
    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a user."""

    pass


class UserRead(UserBase):
    """Schema for reading user data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
