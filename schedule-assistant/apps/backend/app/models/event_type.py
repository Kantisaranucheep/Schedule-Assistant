# schedule-assistant/apps/backend/app/models/event_type.py
"""Event type model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.event import Event


class EventType(Base):
    """Event type model for categorizing events."""

    __tablename__ = "event_types"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_event_types_user_name"),
    )

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
    color: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="event_types")
    events: Mapped[List["Event"]] = relationship("Event", back_populates="event_type")
