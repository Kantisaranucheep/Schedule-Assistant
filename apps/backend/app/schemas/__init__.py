"""Pydantic schemas for API validation."""

from .calendar import CalendarCreate, CalendarUpdate, CalendarResponse
from .category import CategoryCreate, CategoryUpdate, CategoryResponse
from .event import EventCreate, EventUpdate, EventResponse
from .task import TaskCreate, TaskUpdate, TaskResponse
from .chat import ChatRequest, ChatResponse, ChatSessionResponse, ChatMessageResponse
from .settings import UserSettingsCreate, UserSettingsUpdate, UserSettingsResponse

__all__ = [
    "CalendarCreate",
    "CalendarUpdate",
    "CalendarResponse",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "EventCreate",
    "EventUpdate",
    "EventResponse",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "ChatRequest",
    "ChatResponse",
    "ChatSessionResponse",
    "ChatMessageResponse",
    "UserSettingsCreate",
    "UserSettingsUpdate",
    "UserSettingsResponse",
]
