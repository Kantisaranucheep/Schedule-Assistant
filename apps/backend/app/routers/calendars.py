"""Calendar CRUD endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import CalendarCreate, CalendarUpdate, CalendarResponse
from app.services import CalendarService

router = APIRouter(prefix="/calendars", tags=["calendars"])


@router.get("", response_model=List[CalendarResponse])
async def list_calendars(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all calendars for a user."""
    service = CalendarService(db)
    return await service.get_by_user(user_id)


@router.get("/{calendar_id}", response_model=CalendarResponse)
async def get_calendar(
    calendar_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific calendar."""
    service = CalendarService(db)
    calendar = await service.get(calendar_id)
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return calendar


@router.post("", response_model=CalendarResponse, status_code=201)
async def create_calendar(
    data: CalendarCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new calendar."""
    service = CalendarService(db)
    return await service.create(data)


@router.patch("/{calendar_id}", response_model=CalendarResponse)
async def update_calendar(
    calendar_id: UUID,
    data: CalendarUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a calendar."""
    service = CalendarService(db)
    calendar = await service.update(calendar_id, data)
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return calendar


@router.delete("/{calendar_id}", status_code=204)
async def delete_calendar(
    calendar_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a calendar."""
    service = CalendarService(db)
    deleted = await service.delete(calendar_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Calendar not found")
