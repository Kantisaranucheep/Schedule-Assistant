"""User and UserSettings models."""

import uuid
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .calendar import Calendar
    from .chat import ChatSession


class User(BaseModel):
    """User account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Bangkok")

    # Relationships
    calendars: Mapped[List["Calendar"]] = relationship(
        "Calendar", back_populates="user", cascade="all, delete-orphan"
    )
    settings: Mapped[Optional["UserSettings"]] = relationship(
        "UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )


class UserSettings(BaseModel):
    """User preferences."""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    working_hours_start: Mapped[str] = mapped_column(String(5), default="09:00")
    working_hours_end: Mapped[str] = mapped_column(String(5), default="18:00")
    buffer_minutes: Mapped[int] = mapped_column(default=10)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings")
