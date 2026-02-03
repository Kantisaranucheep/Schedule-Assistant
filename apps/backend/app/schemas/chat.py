# schedule-assistant/apps/backend/app/schemas/chat.py
"""Chat Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionBase(BaseModel):
    """Base schema for chat session data."""

    title: str | None = None


class ChatSessionCreate(ChatSessionBase):
    """Schema for creating a chat session."""

    user_id: UUID


class ChatSessionRead(ChatSessionBase):
    """Schema for reading chat session data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime


class ChatMessageBase(BaseModel):
    """Base schema for chat message data."""

    role: Literal["user", "assistant", "system", "tool"]
    content: str
    extracted_json: Dict[str, Any] | None = None
    action_json: Dict[str, Any] | None = None
    confidence: Decimal | None = Field(None, ge=0, le=1, decimal_places=3)


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a chat message."""

    pass


class ChatMessageRead(ChatMessageBase):
    """Schema for reading chat message data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    created_at: datetime
