"""Pydantic schemas for API validation."""

from .calendar import CalendarCreate, CalendarUpdate, CalendarResponse
from .category import CategoryCreate, CategoryUpdate, CategoryResponse
from .event import EventCreate, EventUpdate, EventResponse
from .task import TaskCreate, TaskUpdate, TaskResponse
from .chat import ChatRequest, ChatResponse, ChatSessionResponse, ChatMessageResponse
from .settings import UserSettingsCreate, UserSettingsUpdate, UserSettingsResponse
from .auth import LoginRequest, LoginResponse
from .user_profile import (
    UserStoryRequest,
    PriorityUpdateRequest,
    StrategyUpdateRequest,
    PriorityExtractionResponse,
    UserProfileResponse,
    UserProfileWithExtractionResponse,
    EventPriorityRequest,
    EventPriorityResponse,
)

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
    "LoginRequest",
    "LoginResponse",
    "UserStoryRequest",
    "PriorityUpdateRequest",
    "StrategyUpdateRequest",
    "PriorityExtractionResponse",
    "UserProfileResponse",
    "UserProfileWithExtractionResponse",
    "EventPriorityRequest",
    "EventPriorityResponse",
]
