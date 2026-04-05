"""Category schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    """Base category fields."""

    name: str = Field(..., max_length=100)
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoryCreate(CategoryBase):
    """Create category request."""

    calendar_id: UUID


class CategoryUpdate(BaseModel):
    """Update category request."""

    name: Optional[str] = Field(default=None, max_length=100)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoryResponse(CategoryBase):
    """Category response."""

    id: UUID
    calendar_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
