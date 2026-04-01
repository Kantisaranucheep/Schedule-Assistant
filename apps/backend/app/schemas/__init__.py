"""Pydantic schemas for API validation."""

from .calendar import CalendarCreate, CalendarUpdate, CalendarResponse
from .event import EventCreate, EventUpdate, EventResponse
from .chat import ChatRequest, ChatResponse, ChatSessionResponse, ChatMessageResponse
from .settings import UserSettingsCreate, UserSettingsUpdate, UserSettingsResponse

__all__ = [
    "CalendarCreate",
    "CalendarUpdate",
    "CalendarResponse",
    "EventCreate",
    "EventUpdate",
    "EventResponse",
    "ChatRequest",
    "ChatResponse",
    "ChatSessionResponse",
    "ChatMessageResponse",
    "UserSettingsCreate",
    "UserSettingsUpdate",
    "UserSettingsResponse",
]
