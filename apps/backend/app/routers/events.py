"""Event CRUD endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import EventCreate, EventUpdate, EventResponse
from app.services import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=List[EventResponse])
async def list_events(
    calendar_id: UUID,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get events for a calendar."""
    service = EventService(db)
    return await service.get_by_calendar(calendar_id, start_date, end_date)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific event."""
    service = EventService(db)
    event = await service.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    data: EventCreate,
    check_conflicts: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Create a new event."""
    service = EventService(db)

    if check_conflicts:
        conflicts = await service.check_conflicts(
            data.calendar_id, data.start_time, data.end_time
        )
        if conflicts:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Event conflicts with existing events",
                    "conflicts": [
                        {"id": str(e.id), "title": e.title} for e in conflicts
                    ],
                },
            )

    return await service.create(data)


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    check_conflicts: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Update an event."""
    service = EventService(db)

    if check_conflicts and (data.start_time or data.end_time):
        existing = await service.get(event_id)
        if existing:
            start = data.start_time or existing.start_time
            end = data.end_time or existing.end_time
            conflicts = await service.check_conflicts(
                existing.calendar_id, start, end, exclude_event_id=event_id
            )
            if conflicts:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Event conflicts with existing events",
                        "conflicts": [
                            {"id": str(e.id), "title": e.title} for e in conflicts
                        ],
                    },
                )

    event = await service.update(event_id, data)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: UUID,
    soft: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Delete an event (soft delete by default)."""
    service = EventService(db)
    deleted = await service.delete(event_id, soft=soft)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")


@router.get("/conflicts/check")
async def check_conflicts(
    calendar_id: UUID,
    start_time: datetime,
    end_time: datetime,
    exclude_event_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Check for event conflicts."""
    service = EventService(db)
    conflicts = await service.check_conflicts(
        calendar_id, start_time, end_time, exclude_event_id
    )
    return {
        "has_conflicts": len(conflicts) > 0,
        "conflicts": [
            {"id": str(e.id), "title": e.title, "start": e.start_time, "end": e.end_time}
            for e in conflicts
        ],
    }
