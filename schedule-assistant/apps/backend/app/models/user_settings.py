# schedule-assistant/apps/backend/app/models/user_settings.py
"""User settings model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Any

from sqlalchemy import ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(Base):
    """User settings model for user preferences."""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    timezone: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'Asia/Bangkok'"),
    )
    default_duration_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("60"),
    )
    buffer_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("10"),
    )
    preferences: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
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
    user: Mapped["User"] = relationship("User", back_populates="settings")
