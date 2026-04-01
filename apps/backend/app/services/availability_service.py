"""Availability service - find free time slots."""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_service import EventService


class AvailabilityService:
    """Find available time slots."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_service = EventService(db)

    async def find_free_slots(
        self,
        calendar_id: UUID,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 60,
        working_hours_start: str = "09:00",
        working_hours_end: str = "18:00",
    ) -> List[Dict[str, Any]]:
        """Find available time slots within date range."""
        events = await self.event_service.get_by_calendar(
            calendar_id, start_date, end_date
        )

        free_slots = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        wh_start_h, wh_start_m = map(int, working_hours_start.split(":"))
        wh_end_h, wh_end_m = map(int, working_hours_end.split(":"))

        while current_date <= end_date:
            # Working hours for this day
            day_start = current_date.replace(hour=wh_start_h, minute=wh_start_m)
            day_end = current_date.replace(hour=wh_end_h, minute=wh_end_m)

            # Get events for this day
            day_events = [
                e for e in events
                if e.start_time.date() == current_date.date()
            ]
            day_events.sort(key=lambda e: e.start_time)

            # Find gaps
            slot_start = day_start
            for event in day_events:
                if event.start_time > slot_start:
                    gap_minutes = (event.start_time - slot_start).total_seconds() / 60
                    if gap_minutes >= duration_minutes:
                        free_slots.append({
                            "start": slot_start.isoformat(),
                            "end": event.start_time.isoformat(),
                            "duration_minutes": int(gap_minutes),
                        })
                slot_start = max(slot_start, event.end_time)

            # Check remaining time until end of working hours
            if slot_start < day_end:
                gap_minutes = (day_end - slot_start).total_seconds() / 60
                if gap_minutes >= duration_minutes:
                    free_slots.append({
                        "start": slot_start.isoformat(),
                        "end": day_end.isoformat(),
                        "duration_minutes": int(gap_minutes),
                    })

            current_date += timedelta(days=1)

        return free_slots
