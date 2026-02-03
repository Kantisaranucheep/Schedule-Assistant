# schedule-assistant/apps/backend/app/models/user.py
"""User model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.calendar import Calendar
    from app.models.event_type import EventType
    from app.models.user_settings import UserSettings
    from app.models.chat_session import ChatSession


class User(Base):
    """User model representing application users."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    calendars: Mapped[List["Calendar"]] = relationship(
        "Calendar", back_populates="user", cascade="all, delete-orphan"
    )
    event_types: Mapped[List["EventType"]] = relationship(
        "EventType", back_populates="user", cascade="all, delete-orphan"
    )
    settings: Mapped["UserSettings"] = relationship(
        "UserSettings", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
