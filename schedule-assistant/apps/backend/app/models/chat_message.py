# schedule-assistant/apps/backend/app/models/chat_message.py
"""Chat message model."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.chat_session import ChatSession


class ChatMessage(Base):
    """Chat message model for AI conversation messages."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system', 'tool')",
            name="ck_chat_messages_role",
        ),
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_json: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    action_json: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
