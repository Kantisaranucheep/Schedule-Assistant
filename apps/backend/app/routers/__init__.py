"""API routers."""

from .health import router as health_router
from .calendars import router as calendars_router
from .categories import router as categories_router
from .events import router as events_router

from .tasks import router as tasks_router
from .availability import router as availability_router
from .settings import router as settings_router
from .auth import router as auth_router
from .collaborators import router as collaborators_router
from .user_profile import router as user_profile_router

# Note: chat router is now imported directly from app.chat.router in main.py

__all__ = [
    "health_router",
    "calendars_router",
    "categories_router",
    "events_router",
    "tasks_router",
    "availability_router",
    "settings_router",
    "auth_router",
    "collaborators_router",
    "user_profile_router",
]
