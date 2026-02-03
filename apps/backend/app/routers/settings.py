# schedule-assistant/apps/backend/app/routers/settings.py
"""User settings endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.user_settings import UserSettings
from app.models.user import User
from app.schemas.settings import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsRead)
async def get_settings(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserSettings:
    """Get user settings."""
    settings = await db.get(UserSettings, user_id)
    if not settings:
        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        # Create default settings
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
    return settings


@router.put("", response_model=SettingsRead)
async def update_settings(
    user_id: UUID,
    data: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserSettings:
    """Update user settings."""
    settings = await db.get(UserSettings, user_id)
    if not settings:
        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        # Create settings with provided data
        settings = UserSettings(
            user_id=user_id,
            **data.model_dump(exclude_unset=True),
        )
        db.add(settings)
    else:
        # Update existing settings
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)

    await db.flush()
    await db.refresh(settings)
    return settings
