# schedule-assistant/apps/backend/app/services/conflicts.py
"""Event conflict detection service."""

from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event


async def check_event_conflicts(
    db: AsyncSession,
    calendar_id: UUID,
    start_at: datetime,
    end_at: datetime,
    exclude_event_id: UUID | None = None,
) -> List[Event]:
    """
    Check for conflicting events in the same calendar.

    An event conflicts if:
    - It belongs to the same calendar
    - It's not cancelled
    - Its time range overlaps with the given range
    - It's not the event being updated (if exclude_event_id is provided)

    Args:
        db: Database session
        calendar_id: Calendar to check
        start_at: Start time of new/updated event
        end_at: End time of new/updated event
        exclude_event_id: Event ID to exclude (for updates)

    Returns:
        List of conflicting events
    """
    # Build query for overlapping events
    # Two events overlap if: start1 < end2 AND end1 > start2
    conditions = [
        Event.calendar_id == calendar_id,
        Event.status != "cancelled",
        Event.start_at < end_at,
        Event.end_at > start_at,
    ]

    # Exclude the event being updated
    if exclude_event_id is not None:
        conditions.append(Event.id != exclude_event_id)

    result = await db.execute(
        select(Event).where(and_(*conditions))
    )

    return list(result.scalars().all())
