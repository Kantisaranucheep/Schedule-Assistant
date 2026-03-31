# schedule-assistant/apps/backend/app/routers/__init__.py
"""API routers."""

from app.routers.health import router as health_router
from app.routers.events import router as events_router
from app.routers.agent import router as agent_router

__all__ = [
    "health_router",
    "events_router",
    "agent_router",
]
