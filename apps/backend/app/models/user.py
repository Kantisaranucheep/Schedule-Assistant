"""User and UserSettings models."""

import uuid
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .calendar import Calendar
    from .chat import ChatSession


class User(BaseModel):
    """User account."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
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
    """User preferences including notification settings."""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    working_hours_start: Mapped[str] = mapped_column(String(5), default="09:00")
    working_hours_end: Mapped[str] = mapped_column(String(5), default="18:00")
    buffer_minutes: Mapped[int] = mapped_column(default=10)
    
    # Notification settings
    notification_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    window_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Notification times stored as JSON string: e.g., "[1440, 720]" for 1 day (1440 min) and 12 hours (720 min)
    # Max 2 times, each <= 1440 minutes (1 day) before event
    notification_times_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="[]")

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings")
