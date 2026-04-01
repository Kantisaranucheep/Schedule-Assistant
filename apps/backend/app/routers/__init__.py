"""API routers."""

from .health import router as health_router
from .calendars import router as calendars_router
from .events import router as events_router
from .availability import router as availability_router
from .chat import router as chat_router
from .settings import router as settings_router

__all__ = [
    "health_router",
    "calendars_router",
    "events_router",
    "availability_router",
    "chat_router",
    "settings_router",
]
