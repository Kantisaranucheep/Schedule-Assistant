"""Calendar and EventType models."""

import uuid
from typing import List, TYPE_CHECKING

from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .user import User
    from .event import Event
    from .task import Task
    from .category import Category


class Calendar(BaseModel):
    """User calendar."""

    __tablename__ = "calendars"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), default="My Calendar")
    color: Mapped[str] = mapped_column(String(7), default="#3B82F6")  # Hex color
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Bangkok")

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="calendars")
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="calendar", cascade="all, delete-orphan"
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task", back_populates="calendar", cascade="all, delete-orphan"
    )
    categories: Mapped[List["Category"]] = relationship(
        "Category", back_populates="calendar", cascade="all, delete-orphan"
    )


class EventType(BaseModel):
    """Predefined event types with default colors."""

    __tablename__ = "event_types"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#3B82F6")
    icon: Mapped[str] = mapped_column(String(50), default="calendar")
