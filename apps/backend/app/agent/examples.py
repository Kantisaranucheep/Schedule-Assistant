# apps/backend/app/agent/examples.py
"""
Example implementations showing how to connect agent to backend services.

This file demonstrates:
1. How to create events from agent
2. How to query events from agent
3. How to use services from agent

Use these as templates for implementing real functionality.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.calendar import Calendar
from app.schemas.event import EventCreate, EventRead
from app.services.conflicts import check_event_conflicts
from app.services.availability import get_available_slots, TimeSlot
from app.agent.schemas import (
    ExecuteResponse,
    CreateEventData,
    FindFreeSlotsData,
)


# ============================================================================
# EXAMPLE 1: Create Event from Agent
# ============================================================================

async def create_event_from_agent(
    db: AsyncSession,
    calendar_id: UUID,
    data: CreateEventData,
) -> ExecuteResponse:
    """
    Example: Create an event in the database from agent intent.
    
    This shows how to:
    1. Parse agent intent data
    2. Check for conflicts using the service
    3. Create event in database
    4. Return structured response
    
    Args:
        db: Database session (passed from executor)
        calendar_id: Target calendar UUID
        data: Parsed CreateEventData from intent
    
    Returns:
        ExecuteResponse with success/failure and event details
    """
    # 1. Parse datetime from intent data
    start_dt = datetime.strptime(f"{data.date} {data.start_time}", "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(f"{data.date} {data.end_time}", "%Y-%m-%d %H:%M")
    
    # 2. Verify calendar exists
    calendar = await db.get(Calendar, calendar_id)
    if not calendar:
        return ExecuteResponse(
            success=False,
            error=f"Calendar {calendar_id} not found",
            message="The specified calendar doesn't exist.",
        )
    
    # 3. Check for conflicts using the existing service
    conflicts = await check_event_conflicts(
        db=db,
        calendar_id=calendar_id,
        start_at=start_dt,
        end_at=end_dt,
        exclude_event_id=None,
    )
    
    if conflicts:
        # Return conflict info so agent can suggest alternatives
        return ExecuteResponse(
            success=False,
            error="Time conflict with existing events",
            result={
                "conflicting_events": [
                    {
                        "id": str(e.id),
                        "title": e.title,
                        "start": e.start_at.isoformat(),
                        "end": e.end_at.isoformat(),
                    }
                    for e in conflicts
                ]
            },
            message=f"Cannot create event: conflicts with {len(conflicts)} existing event(s).",
        )
    
    # 4. Create the event
    event = Event(
        calendar_id=calendar_id,
        title=data.title,
        description=data.description,
        location=data.location,
        start_at=start_dt,
        end_at=end_dt,
        status="confirmed",
        created_by="agent",  # Important: mark as agent-created
    )
    
    db.add(event)
    await db.flush()  # Get the ID without committing
    
    # 5. Return success response
    return ExecuteResponse(
        success=True,
        result={
            "event_id": str(event.id),
            "title": event.title,
            "start_at": event.start_at.isoformat(),
            "end_at": event.end_at.isoformat(),
            "location": event.location,
            "created_by": event.created_by,
        },
        message=f"✅ Created '{event.title}' on {data.date} from {data.start_time} to {data.end_time}",
    )


# ============================================================================
# EXAMPLE 2: Find Free Slots from Agent
# ============================================================================

async def find_free_slots_from_agent(
    db: AsyncSession,
    calendar_id: UUID,
    user_id: UUID,
    data: FindFreeSlotsData,
) -> ExecuteResponse:
    """
    Example: Find available time slots using the availability service.
    
    This shows how to:
    1. Parse date range from intent
    2. Call the availability service
    3. Filter by duration
    4. Return formatted slots
    
    Args:
        db: Database session
        calendar_id: Calendar to check
        user_id: User for preferences
        data: Parsed FindFreeSlotsData from intent
    
    Returns:
        ExecuteResponse with available slots
    """
    from datetime import date as date_type
    
    # 1. Parse date range
    start_date = datetime.strptime(data.date_range.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(data.date_range.end_date, "%Y-%m-%d").date()
    
    # 2. Collect slots for each day in range
    all_slots: List[dict] = []
    current_date = start_date
    
    while current_date <= end_date:
        # Call the existing availability service
        day_slots = await get_available_slots(
            db=db,
            calendar_id=calendar_id,
            user_id=user_id,
            target_date=current_date,
        )
        
        # Filter by requested duration
        for slot in day_slots:
            slot_duration = (slot.end_at - slot.start_at).total_seconds() / 60
            if slot_duration >= data.duration_minutes:
                all_slots.append({
                    "date": current_date.isoformat(),
                    "start": slot.start_at.strftime("%H:%M"),
                    "end": slot.end_at.strftime("%H:%M"),
                    "duration_minutes": int(slot_duration),
                })
        
        current_date += timedelta(days=1)
    
    # 3. Return response
    if not all_slots:
        return ExecuteResponse(
            success=True,
            result={"slots": []},
            message=f"No {data.duration_minutes}-minute slots available between {data.date_range.start_date} and {data.date_range.end_date}",
        )
    
    return ExecuteResponse(
        success=True,
        result={
            "slot_count": len(all_slots),
            "duration_requested": data.duration_minutes,
            "slots": all_slots[:10],  # Limit to first 10 for readability
        },
        message=f"Found {len(all_slots)} available {data.duration_minutes}-minute slots",
    )


# ============================================================================
# EXAMPLE 3: List Events from Agent
# ============================================================================

async def list_events_from_agent(
    db: AsyncSession,
    calendar_id: UUID,
    target_date: str,
) -> ExecuteResponse:
    """
    Example: List events for a specific date.
    
    This shows a simple database query from agent.
    
    Args:
        db: Database session
        calendar_id: Calendar to query
        target_date: Date string (YYYY-MM-DD)
    
    Returns:
        ExecuteResponse with events list
    """
    # 1. Parse date
    date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    day_start = datetime.combine(date_obj, datetime.min.time())
    day_end = datetime.combine(date_obj, datetime.max.time())
    
    # 2. Query database
    result = await db.execute(
        select(Event)
        .where(
            and_(
                Event.calendar_id == calendar_id,
                Event.start_at >= day_start,
                Event.start_at <= day_end,
                Event.status != "cancelled",
            )
        )
        .order_by(Event.start_at)
    )
    events = result.scalars().all()
    
    # 3. Format response
    event_list = [
        {
            "id": str(e.id),
            "title": e.title,
            "start": e.start_at.strftime("%H:%M"),
            "end": e.end_at.strftime("%H:%M"),
            "location": e.location,
            "status": e.status,
        }
        for e in events
    ]
    
    if not event_list:
        return ExecuteResponse(
            success=True,
            result={"events": []},
            message=f"No events scheduled for {target_date}",
        )
    
    return ExecuteResponse(
        success=True,
        result={
            "date": target_date,
            "event_count": len(event_list),
            "events": event_list,
        },
        message=f"You have {len(event_list)} event(s) on {target_date}",
    )


# ============================================================================
# EXAMPLE 4: Delete Event from Agent
# ============================================================================

async def delete_event_from_agent(
    db: AsyncSession,
    calendar_id: UUID,
    event_id: Optional[str] = None,
    title: Optional[str] = None,
    date: Optional[str] = None,
) -> ExecuteResponse:
    """
    Example: Delete an event by ID or by title+date.
    
    This shows how to:
    1. Find event by ID or by searching
    2. Soft delete (change status) vs hard delete
    3. Return confirmation
    
    Args:
        db: Database session
        calendar_id: Calendar scope
        event_id: Event UUID (if known)
        title: Event title (if ID not known)
        date: Event date (if ID not known)
    
    Returns:
        ExecuteResponse with deletion result
    """
    event: Optional[Event] = None
    
    # 1. Find the event
    if event_id:
        # Find by ID
        from uuid import UUID as UUIDType
        event = await db.get(Event, UUIDType(event_id))
        if event and event.calendar_id != calendar_id:
            event = None  # Wrong calendar
    elif title and date:
        # Find by title + date
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        day_start = datetime.combine(date_obj, datetime.min.time())
        day_end = datetime.combine(date_obj, datetime.max.time())
        
        result = await db.execute(
            select(Event)
            .where(
                and_(
                    Event.calendar_id == calendar_id,
                    Event.title.ilike(f"%{title}%"),
                    Event.start_at >= day_start,
                    Event.start_at <= day_end,
                    Event.status != "cancelled",
                )
            )
        )
        event = result.scalar_one_or_none()
    
    if not event:
        return ExecuteResponse(
            success=False,
            error="Event not found",
            message="Could not find the event you want to delete. Please provide more details.",
        )
    
    # 2. Soft delete (mark as cancelled)
    event_title = event.title
    event_date = event.start_at.strftime("%Y-%m-%d")
    event.status = "cancelled"
    
    # 3. Return confirmation
    return ExecuteResponse(
        success=True,
        result={
            "deleted_event_id": str(event.id),
            "title": event_title,
            "date": event_date,
        },
        message=f"🗑️ Cancelled event '{event_title}' on {event_date}",
    )


# ============================================================================
# HOW TO USE THESE IN EXECUTOR
# ============================================================================
"""
To use these functions in executor.py, import and call them:

```python
# In executor.py

from app.agent.examples import (
    create_event_from_agent,
    find_free_slots_from_agent,
    list_events_from_agent,
    delete_event_from_agent,
)

async def _execute_create_event(
    self,
    intent: Intent,
    request: ExecuteRequest,
) -> ExecuteResponse:
    data = CreateEventData(**intent.data)
    
    # Use the example function
    return await create_event_from_agent(
        db=self.db,
        calendar_id=request.calendar_id,
        data=data,
    )
```
"""
