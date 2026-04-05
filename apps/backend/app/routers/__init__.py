"""API routers."""

from .health import router as health_router
from .calendars import router as calendars_router
from .categories import router as categories_router
from .events import router as events_router
from .tasks import router as tasks_router
from .availability import router as availability_router
from .chat import router as chat_router
from .chat_v2 import router as chat_v2_router
from .settings import router as settings_router

__all__ = [
    "health_router",
    "calendars_router",
    "categories_router",
    "events_router",
    "tasks_router",
    "availability_router",
    "chat_router",
    "chat_v2_router",
    "settings_router",
]
