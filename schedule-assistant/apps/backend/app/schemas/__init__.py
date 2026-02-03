# schedule-assistant/apps/backend/app/schemas/__init__.py
"""Pydantic schemas for request/response validation."""

from app.schemas.user import UserBase, UserCreate, UserRead
from app.schemas.calendar import CalendarBase, CalendarCreate, CalendarRead
from app.schemas.event_type import EventTypeBase, EventTypeCreate, EventTypeRead
from app.schemas.event import EventBase, EventCreate, EventUpdate, EventRead
from app.schemas.chat import (
    ChatSessionBase,
    ChatSessionCreate,
    ChatSessionRead,
    ChatMessageBase,
    ChatMessageCreate,
    ChatMessageRead,
)
from app.schemas.settings import SettingsBase, SettingsUpdate, SettingsRead

__all__ = [
    "UserBase",
    "UserCreate",
    "UserRead",
    "CalendarBase",
    "CalendarCreate",
    "CalendarRead",
    "EventTypeBase",
    "EventTypeCreate",
    "EventTypeRead",
    "EventBase",
    "EventCreate",
    "EventUpdate",
    "EventRead",
    "ChatSessionBase",
    "ChatSessionCreate",
    "ChatSessionRead",
    "ChatMessageBase",
    "ChatMessageCreate",
    "ChatMessageRead",
    "SettingsBase",
    "SettingsUpdate",
    "SettingsRead",
]
