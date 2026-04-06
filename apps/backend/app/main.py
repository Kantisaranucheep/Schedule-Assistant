"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
# Import models to register with Base.metadata
from app.models import User, UserSettings, Calendar, EventType, Category, Event, Task, ChatSession, ChatMessage
from app.routers import (
    health_router,
    calendars_router,
    categories_router,
    events_router,
    tasks_router,
    availability_router,
    settings_router,
)
# Import new chat router (replaces old agent/chat system)
from app.chat.router import router as chat_agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup: create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: dispose engine
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
app.include_router(health_router)
app.include_router(calendars_router)
app.include_router(categories_router)
app.include_router(events_router)
app.include_router(tasks_router)
app.include_router(availability_router)
app.include_router(chat_agent_router)  # New chat agent system
app.include_router(settings_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
    }
