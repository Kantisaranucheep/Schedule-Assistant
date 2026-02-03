# schedule-assistant/apps/backend/app/models/calendar.py
"""Calendar model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.event import Event


class Calendar(Base):
    """Calendar model for organizing events."""

    __tablename__ = "calendars"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="calendars")
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="calendar", cascade="all, delete-orphan"
    )
