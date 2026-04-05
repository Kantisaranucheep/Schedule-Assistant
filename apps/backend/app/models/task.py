"""Task model."""

import uuid
from datetime import date as date_type
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .calendar import Calendar
    from .category import Category


class Task(BaseModel):
    """Calendar task - similar to event but only has a date, no time."""

    __tablename__ = "tasks"

    calendar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calendars.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    date: Mapped[date_type] = mapped_column(Date, index=True)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, completed, cancelled

    # Relationships
    calendar: Mapped["Calendar"] = relationship("Calendar", back_populates="tasks")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="tasks")
