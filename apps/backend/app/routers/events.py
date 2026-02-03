# schedule-assistant/apps/backend/app/routers/events.py
"""Event endpoints."""

from datetime import datetime, date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.event import Event
from app.models.calendar import Calendar
from app.schemas.event import EventCreate, EventRead, EventUpdate
from app.services.conflicts import check_event_conflicts
from app.services.availability import get_available_slots, TimeSlot

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=List[EventRead])
async def list_events(
    calendar_id: UUID,
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
) -> List[Event]:
    """List events within a date range."""
    result = await db.execute(
        select(Event)
        .where(
            Event.calendar_id == calendar_id,
            Event.start_at >= from_,
            Event.end_at <= to,
        )
        .order_by(Event.start_at)
    )
    return list(result.scalars().all())


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
) -> Event:
    """Create a new event with conflict detection."""
    # Verify calendar exists
    calendar = await db.get(Calendar, data.calendar_id)
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar {data.calendar_id} not found",
        )

    # Check for conflicts
    conflicts = await check_event_conflicts(
        db=db,
        calendar_id=data.calendar_id,
        start_at=data.start_at,
        end_at=data.end_at,
        exclude_event_id=None,
    )
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Event conflicts with existing events",
                "conflicting_event_ids": [str(e.id) for e in conflicts],
            },
        )

    event = Event(
        calendar_id=data.calendar_id,
        type_id=data.type_id,
        title=data.title,
        description=data.description,
        location=data.location,
        start_at=data.start_at,
        end_at=data.end_at,
        status=data.status,
        created_by=data.created_by,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.put("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
) -> Event:
    """Update an event with conflict detection."""
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found",
        )

    # Determine new start/end times
    new_start = data.start_at if data.start_at is not None else event.start_at
    new_end = data.end_at if data.end_at is not None else event.end_at

    # Validate end > start
    if new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_at must be after start_at",
        )

    # Check for conflicts (exclude this event)
    conflicts = await check_event_conflicts(
        db=db,
        calendar_id=event.calendar_id,
        start_at=new_start,
        end_at=new_end,
        exclude_event_id=event_id,
    )
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Event conflicts with existing events",
                "conflicting_event_ids": [str(e.id) for e in conflicts],
            },
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    event.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an event."""
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found",
        )
    await db.delete(event)


@router.get("/availability")
async def get_availability(
    calendar_id: UUID,
    date_param: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get available time slots for a specific date."""
    # Verify calendar exists and get user settings
    calendar = await db.get(Calendar, calendar_id)
    if not calendar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar {calendar_id} not found",
        )

    slots = await get_available_slots(
        db=db,
        calendar_id=calendar_id,
        user_id=calendar.user_id,
        target_date=date_param,
    )

    return {
        "date": date_param.isoformat(),
        "calendar_id": str(calendar_id),
        "slots": [{"start_at": s.start_at.isoformat(), "end_at": s.end_at.isoformat()} for s in slots],
    }
