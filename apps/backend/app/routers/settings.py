"""User settings endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import UserSettings
from app.schemas import UserSettingsCreate, UserSettingsUpdate, UserSettingsResponse

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/{user_id}", response_model=UserSettingsResponse)
async def get_settings(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get user settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings


@router.post("", response_model=UserSettingsResponse, status_code=201)
async def create_settings(
    data: UserSettingsCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create user settings."""
    settings = UserSettings(**data.model_dump())
    db.add(settings)
    await db.flush()
    await db.refresh(settings)
    return settings


@router.patch("/{user_id}", response_model=UserSettingsResponse)
async def update_settings(
    user_id: UUID,
    data: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update user settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.flush()
    await db.refresh(settings)
    return settings
