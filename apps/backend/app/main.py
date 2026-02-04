# schedule-assistant/apps/backend/app/main.py
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import (
    health_router,
    calendars_router,
    events_router,
    chat_router,
    settings_router,
    agent_router,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API for Schedule Assistant application",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(calendars_router)
app.include_router(events_router)
app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(agent_router)


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
