# schedule-assistant/apps/backend/app/routers/__init__.py
"""API routers."""

from app.routers.health import router as health_router
from app.routers.calendars import router as calendars_router
from app.routers.events import router as events_router
from app.routers.chat import router as chat_router
from app.routers.settings import router as settings_router
from app.routers.agent import router as agent_router

__all__ = [
    "health_router",
    "calendars_router",
    "events_router",
    "chat_router",
    "settings_router",
    "agent_router",
]
