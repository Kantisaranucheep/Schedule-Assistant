# schedule-assistant/apps/backend/app/models/event.py
"""Event model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.calendar import Calendar
    from app.models.event_type import EventType


class Event(Base):
    """Event model representing calendar events."""

    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_events_end_after_start"),
        CheckConstraint(
            "status IN ('confirmed', 'tentative', 'cancelled')",
            name="ck_events_status",
        ),
        CheckConstraint(
            "created_by IN ('user', 'agent')",
            name="ck_events_created_by",
        ),
        Index("ix_events_calendar_start", "calendar_id", "start_at"),
        Index("ix_events_calendar_start_end", "calendar_id", "start_at", "end_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    calendar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    end_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'confirmed'"),
    )
    created_by: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'user'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
    )

    # Relationships
    calendar: Mapped["Calendar"] = relationship("Calendar", back_populates="events")
    event_type: Mapped["EventType"] = relationship("EventType", back_populates="events")
