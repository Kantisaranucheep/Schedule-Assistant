"""Event CRUD endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import EventCreate, EventUpdate, EventResponse
from app.services import EventService
from app.services.event_service import ensure_timezone_aware
from app.chat.prolog_service import get_prolog_service
from app.chat.event_repository import EventRepository

DEFAULT_TIMEZONE = "Asia/Bangkok"

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
        prolog = get_prolog_service()
        tz_name = getattr(data, "timezone", None) or DEFAULT_TIMEZONE
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)
            tz_name = DEFAULT_TIMEZONE

        # Convert to local timezone to match EventRepository._event_to_dict output
        local_start = ensure_timezone_aware(data.start_time).astimezone(tz)
        local_end = ensure_timezone_aware(data.end_time).astimezone(tz)

        repo = EventRepository(db, timezone=tz_name)
        existing_events = await repo.get_events_on_date(
            local_start.day, local_start.month, local_start.year,
            calendar_id=data.calendar_id,
        )
        conflict_result = prolog.check_conflict(
            local_start.hour, local_start.minute,
            local_end.hour, local_end.minute,
            existing_events,
        )
        if conflict_result.has_conflict:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Event conflicts with existing events",
                    "conflicts": [
                        {"id": str(c.get("id", "")), "title": c["title"]}
                        for c in conflict_result.conflicts
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
        existing = await service._get_raw(event_id)
        if existing:
            start = data.start_time or existing.start_time
            end = data.end_time or existing.end_time
            prolog = get_prolog_service()
            tz_name = getattr(data, "timezone", None) or DEFAULT_TIMEZONE
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = ZoneInfo(DEFAULT_TIMEZONE)
                tz_name = DEFAULT_TIMEZONE

            # Convert to local timezone to match EventRepository._event_to_dict output
            local_start = ensure_timezone_aware(start).astimezone(tz)
            local_end = ensure_timezone_aware(end).astimezone(tz)

            repo = EventRepository(db, timezone=tz_name)
            existing_events = await repo.get_events_on_date(
                local_start.day, local_start.month, local_start.year,
                calendar_id=existing.calendar_id,
            )
            existing_events = [e for e in existing_events if str(e.get("id")) != str(event_id)]
            conflict_result = prolog.check_conflict(
                local_start.hour, local_start.minute,
                local_end.hour, local_end.minute,
                existing_events,
            )
            if conflict_result.has_conflict:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Event conflicts with existing events",
                        "conflicts": [
                            {"id": str(c.get("id", "")), "title": c["title"]}
                            for c in conflict_result.conflicts
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
    """Check for event conflicts using Prolog reasoning."""
    prolog = get_prolog_service()
    tz = ZoneInfo(DEFAULT_TIMEZONE)

    # Convert to local timezone to match EventRepository._event_to_dict output
    local_start = ensure_timezone_aware(start_time).astimezone(tz)
    local_end = ensure_timezone_aware(end_time).astimezone(tz)

    repo = EventRepository(db, timezone=DEFAULT_TIMEZONE)
    existing_events = await repo.get_events_on_date(
        local_start.day, local_start.month, local_start.year,
        calendar_id=calendar_id,
    )
    if exclude_event_id:
        existing_events = [e for e in existing_events if str(e.get("id")) != str(exclude_event_id)]
    conflict_result = prolog.check_conflict(
        local_start.hour, local_start.minute,
        local_end.hour, local_end.minute,
        existing_events,
    )
    return {
        "has_conflicts": conflict_result.has_conflict,
        "conflicts": [
            {
                "id": str(c.get("id", "")),
                "title": c["title"],
                "start": f"{c['start_hour']:02d}:{c['start_minute']:02d}",
                "end": f"{c['end_hour']:02d}:{c['end_minute']:02d}",
            }
            for c in conflict_result.conflicts
        ],
    }
