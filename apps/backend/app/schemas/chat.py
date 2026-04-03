"""Chat schemas - matches frontend LLMChatResponse interface."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request from frontend."""

    message: str = Field(..., min_length=1)
    session_id: str  # Frontend uses string UUIDs
    execute_intent: bool = True
    calendar_id: Optional[str] = None
    user_id: Optional[str] = None
    timezone: Optional[str] = Field(default="Asia/Bangkok", description="User's IANA timezone")


class IntentData(BaseModel):
    """Intent extracted by agent."""

    intent: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    """Result of executing an intent."""

    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    event: Optional[Dict[str, Any]] = None
    events: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    """Chat response - matches frontend LLMChatResponse."""

    reply: str
    error: Optional[str] = None
    intent: Optional[IntentData] = None
    action_result: Optional[ActionResult] = None


class ChatMessageResponse(BaseModel):
    """Chat message response."""

    id: UUID
    role: str
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    """Chat session response."""

    id: UUID
    title: str
    created_at: datetime
    messages: List[ChatMessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
