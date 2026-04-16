"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.timezone import get_system_timezone_name, SYSTEM_TIMEZONE
# Import models to register with Base.metadata
from app.models import User, UserSettings, UserProfile, Calendar, EventType, Category, Event, Task, ChatSession, ChatMessage
from app.routers import (
    health_router,
    calendars_router,
    categories_router,
    events_router,
    tasks_router,
    availability_router,
    settings_router,
    auth_router,
    user_profile_router,
    scheduling_router,
)
from app.chat.router import router as chat_agent_router
from app.routers.ws import router as ws_router
# Import notification scheduler
from app.services import start_notification_scheduler, stop_notification_scheduler, get_email_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Log timezone info at startup
    logger.info(f"🕐 System timezone detected: {get_system_timezone_name()}")
    logger.info(f"📅 Default timezone set to: {settings.default_timezone}")
    
    # Startup: create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Start notification scheduler
    email_service = get_email_service()
    if email_service.is_configured():
        start_notification_scheduler()
        logger.info("📧 Email notification scheduler started")
    else:
        error_msg = email_service.get_config_error_message()
        logger.warning(f"📧 {error_msg}")
    
    yield
    
    # Shutdown: stop scheduler and dispose engine
    stop_notification_scheduler()
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - allow all origins in development
origins = settings.cors_origins_list
# Ensure localhost:3000 is always included for development
if "http://localhost:3000" not in origins:
    origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers

from app.routers import collaborators_router
app.include_router(health_router)
app.include_router(calendars_router)
app.include_router(categories_router)
app.include_router(events_router)
app.include_router(tasks_router)
app.include_router(availability_router)
app.include_router(chat_agent_router)  # New chat agent system
app.include_router(settings_router)
app.include_router(auth_router)
app.include_router(collaborators_router)
app.include_router(user_profile_router)  # User profile/persona system
app.include_router(scheduling_router)   # Priority-aware scheduling with A*
app.include_router(ws_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
    }
