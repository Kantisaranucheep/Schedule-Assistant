# schedule-assistant/apps/backend/app/services/availability.py
"""Availability calculation service."""

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import List
from uuid import UUID
import zoneinfo

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.event import Event
from app.models.user_settings import UserSettings


@dataclass
class TimeSlot:
    """Represents an available time slot."""

    start_at: datetime
    end_at: datetime


def parse_time(time_str: str) -> time:
    """Parse time string (HH:MM) to time object."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


async def get_available_slots(
    db: AsyncSession,
    calendar_id: UUID,
    user_id: UUID,
    target_date: date,
) -> List[TimeSlot]:
    """
    Calculate available time slots for a specific date.

    Takes into account:
    - User's working hours preference (default 09:00-18:00)
    - Existing events in the calendar
    - Buffer time around events

    Args:
        db: Database session
        calendar_id: Calendar to check
        user_id: User who owns the calendar
        target_date: Date to get availability for

    Returns:
        List of available time slots
    """
    settings = get_settings()

    # Get user settings
    user_settings = await db.get(UserSettings, user_id)

    # Determine timezone and working hours
    tz_str = settings.default_timezone
    working_start_str = settings.default_working_hours_start
    working_end_str = settings.default_working_hours_end
    buffer_min = 10

    if user_settings:
        tz_str = user_settings.timezone or tz_str
        buffer_min = user_settings.buffer_min or buffer_min
        # Check preferences for working hours
        prefs = user_settings.preferences or {}
        working_start_str = prefs.get("working_hours_start", working_start_str)
        working_end_str = prefs.get("working_hours_end", working_end_str)

    # Parse working hours
    working_start = parse_time(working_start_str)
    working_end = parse_time(working_end_str)

    # Get timezone
    try:
        tz = zoneinfo.ZoneInfo(tz_str)
    except Exception:
        tz = zoneinfo.ZoneInfo("UTC")

    # Build datetime range for the day
    day_start = datetime.combine(target_date, working_start, tzinfo=tz)
    day_end = datetime.combine(target_date, working_end, tzinfo=tz)

    # Get events for this day (including buffer time consideration)
    search_start = day_start - timedelta(minutes=buffer_min)
    search_end = day_end + timedelta(minutes=buffer_min)

    result = await db.execute(
        select(Event)
        .where(
            and_(
                Event.calendar_id == calendar_id,
                Event.status != "cancelled",
                Event.start_at < search_end,
                Event.end_at > search_start,
            )
        )
        .order_by(Event.start_at)
    )
    events = list(result.scalars().all())

    # Calculate available slots
    slots: List[TimeSlot] = []
    buffer = timedelta(minutes=buffer_min)

    # Create list of busy periods (with buffer)
    busy_periods: List[tuple[datetime, datetime]] = []
    for event in events:
        # Ensure event times are timezone-aware
        event_start = event.start_at
        event_end = event.end_at

        # Add buffer around events
        busy_start = event_start - buffer
        busy_end = event_end + buffer

        busy_periods.append((busy_start, busy_end))

    # Merge overlapping busy periods
    if busy_periods:
        busy_periods.sort(key=lambda x: x[0])
        merged: List[tuple[datetime, datetime]] = [busy_periods[0]]
        for current_start, current_end in busy_periods[1:]:
            last_start, last_end = merged[-1]
            if current_start <= last_end:
                # Overlapping, merge
                merged[-1] = (last_start, max(last_end, current_end))
            else:
                merged.append((current_start, current_end))
        busy_periods = merged

    # Find free slots between busy periods
    current_time = day_start

    for busy_start, busy_end in busy_periods:
        # Clip busy period to working hours
        busy_start = max(busy_start, day_start)
        busy_end = min(busy_end, day_end)

        if current_time < busy_start:
            # There's a free slot before this busy period
            slots.append(TimeSlot(start_at=current_time, end_at=busy_start))

        # Move current time to end of busy period
        current_time = max(current_time, busy_end)

    # Check if there's time after the last busy period
    if current_time < day_end:
        slots.append(TimeSlot(start_at=current_time, end_at=day_end))

    # If no events, the entire working hours are available
    if not busy_periods:
        slots = [TimeSlot(start_at=day_start, end_at=day_end)]

    return slots
