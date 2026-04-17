"""Models for event collaboration and invitations."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import BaseModel

class EventCollaborator(BaseModel):
    __tablename__ = "event_collaborators"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # For future: role (e.g., 'editor', 'viewer')
    role: Mapped[str] = mapped_column(String(20), default="editor")

class EventCollaborationInvitation(BaseModel):
    __tablename__ = "event_collaboration_invitations"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), index=True)
    inviter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    invitee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, accepted, declined, conflict_reported
    responded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    conflict_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # message when conflict is reported
