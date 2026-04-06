# apps/backend/app/chat/schemas.py
"""
Pydantic schemas for chat API requests and responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Type of message in the chat."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ChoiceOption(BaseModel):
    """A clickable choice option for the user."""
    
    id: str = Field(..., description="Unique identifier for this choice")
    label: str = Field(..., description="Display text for the button")
    value: str = Field(..., description="Value to send when clicked")
    
    model_config = {"from_attributes": True}


class AgentMessage(BaseModel):
    """A message from the agent with optional choices."""
    
    text: str = Field(..., description="The message text")
    choices: Optional[List[ChoiceOption]] = Field(
        default=None, 
        description="Optional list of choice buttons"
    )
    requires_response: bool = Field(
        default=False,
        description="Whether the agent is waiting for user response"
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        description="Timeout in seconds for choice selection"
    )
    
    model_config = {"from_attributes": True}


class SessionState(BaseModel):
    """Current state of the chat session."""
    
    state: str = Field(..., description="Current agent state")
    intent: Optional[str] = Field(default=None, description="Current intent type")
    event_data: Optional[Dict[str, Any]] = Field(default=None, description="Event data being processed")
    conflict_info: Optional[Dict[str, Any]] = Field(default=None, description="Conflict information if any")
    
    model_config = {"from_attributes": True}


class ChatMessageRequest(BaseModel):
    """Request to send a message to the chat agent."""
    
    message: str = Field(..., min_length=1, description="The user's message")
    session_id: Optional[str] = Field(
        default=None, 
        description="Session ID for continuing conversation"
    )
    calendar_id: Optional[str] = Field(
        default=None,
        description="Calendar ID for event operations"
    )
    timezone: str = Field(
        default="Asia/Bangkok",
        description="User's timezone (IANA format)"
    )
    
    model_config = {"from_attributes": True}


class ChatChoiceRequest(BaseModel):
    """Request when user clicks a choice button."""
    
    session_id: str = Field(..., description="Session ID")
    choice_id: str = Field(..., description="ID of the selected choice")
    choice_value: str = Field(..., description="Value of the selected choice")
    
    model_config = {"from_attributes": True}


class ChatAgentResponse(BaseModel):
    """Response from the chat agent."""
    
    session_id: str = Field(..., description="Session ID for this conversation")
    message: AgentMessage = Field(..., description="The agent's response message")
    state: SessionState = Field(..., description="Current session state")
    success: bool = Field(default=True, description="Whether the operation succeeded")
    error: Optional[str] = Field(default=None, description="Error message if any")
    event_created: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Created event data if an event was created"
    )
    event_updated: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated event data if an event was modified"
    )
    event_deleted: Optional[str] = Field(
        default=None,
        description="ID of deleted event if an event was removed"
    )
    events_list: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of events for query responses"
    )
    
    model_config = {"from_attributes": True}


class ChatTerminateRequest(BaseModel):
    """Request to terminate current chat session."""
    
    session_id: str = Field(..., description="Session ID to terminate")
    
    model_config = {"from_attributes": True}


class ChatTerminateResponse(BaseModel):
    """Response after terminating chat session."""
    
    session_id: str
    terminated: bool = True
    message: str = "Session terminated. All conversation data discarded."
    
    model_config = {"from_attributes": True}


class ChatSessionInfo(BaseModel):
    """Information about a chat session."""
    
    session_id: str
    state: str
    created_at: datetime
    last_activity: datetime
    
    model_config = {"from_attributes": True}


# Intent parsing response from LLM
class ParsedIntent(BaseModel):
    """Structured intent parsed from user message by LLM."""
    
    intent: str = Field(..., description="The detected intent type")
    event: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Event data extracted from message"
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description="Fields that are missing and need to be collected"
    )
    target_event: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Target event for edit/remove operations"
    )
    query: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Query parameters for list operations"
    )
    
    model_config = {"from_attributes": True}


class YesNoResponse(BaseModel):
    """Response for yes/no questions."""
    
    answer: bool = Field(..., description="True for positive, False for negative")
    
    model_config = {"from_attributes": True}


class ChoiceResponse(BaseModel):
    """Response for multiple choice questions."""
    
    choice: int = Field(..., ge=1, le=4, description="Selected choice number (1-4)")
    
    model_config = {"from_attributes": True}


class TimeResponse(BaseModel):
    """Response for time-related questions."""
    
    day: Optional[int] = Field(default=None, ge=1, le=31)
    month: Optional[int] = Field(default=None, ge=1, le=12)
    year: Optional[int] = Field(default=None, ge=2020, le=2100)
    start_hour: Optional[int] = Field(default=None, ge=0, le=23)
    start_minute: Optional[int] = Field(default=None, ge=0, le=59)
    end_hour: Optional[int] = Field(default=None, ge=0, le=23)
    end_minute: Optional[int] = Field(default=None, ge=0, le=59)
    
    model_config = {"from_attributes": True}
