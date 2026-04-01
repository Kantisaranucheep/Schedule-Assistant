"""Availability endpoints."""

from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import AvailabilityService

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("/free-slots", response_model=List[Dict[str, Any]])
async def find_free_slots(
    calendar_id: UUID,
    start_date: datetime,
    end_date: datetime,
    duration_minutes: int = Query(60, ge=15, le=480),
    working_hours_start: str = Query("09:00", pattern=r"^\d{2}:\d{2}$"),
    working_hours_end: str = Query("18:00", pattern=r"^\d{2}:\d{2}$"),
    db: AsyncSession = Depends(get_db),
):
    """Find available time slots."""
    service = AvailabilityService(db)
    return await service.find_free_slots(
        calendar_id,
        start_date,
        end_date,
        duration_minutes,
        working_hours_start,
        working_hours_end,
    )
