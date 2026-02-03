# schedule-assistant/apps/backend/app/routers/calendars.py
"""Calendar endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.calendar import Calendar
from app.models.user import User
from app.schemas.calendar import CalendarCreate, CalendarRead

router = APIRouter(prefix="/calendars", tags=["calendars"])


@router.get("", response_model=List[CalendarRead])
async def list_calendars(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[Calendar]:
    """List all calendars for a user."""
    result = await db.execute(
        select(Calendar).where(Calendar.user_id == user_id).order_by(Calendar.created_at)
    )
    return list(result.scalars().all())


@router.post("", response_model=CalendarRead, status_code=status.HTTP_201_CREATED)
async def create_calendar(
    data: CalendarCreate,
    db: AsyncSession = Depends(get_db),
) -> Calendar:
    """Create a new calendar."""
    # Verify user exists
    user = await db.get(User, data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {data.user_id} not found",
        )

    calendar = Calendar(
        user_id=data.user_id,
        name=data.name,
        timezone=data.timezone,
    )
    db.add(calendar)
    await db.flush()
    await db.refresh(calendar)
    return calendar
