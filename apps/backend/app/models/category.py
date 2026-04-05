"""Category model."""

import uuid
from typing import Optional, TYPE_CHECKING, List

from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .calendar import Calendar
    from .event import Event
    from .task import Task


class Category(BaseModel):
    """Event/Task category with name and color."""

    __tablename__ = "categories"

    calendar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calendars.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), default="#3B82F6")  # Hex color

    # Relationships
    calendar: Mapped["Calendar"] = relationship("Calendar", back_populates="categories")
    events: Mapped[List["Event"]] = relationship("Event", back_populates="category")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="category")
