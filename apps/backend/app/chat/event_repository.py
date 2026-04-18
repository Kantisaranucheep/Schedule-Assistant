# apps/backend/app/chat/event_repository.py
"""
Event Repository - Database operations for the chat agent.

This module handles all database interactions for the chat feature,
keeping them separate from the main event service.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, Calendar, UserProfile, EventCollaborator
from app.services.scheduling_service import SchedulingService as _SchedulingService

# Shared instance for type/priority inference (stateless helper methods only)
_svc = _SchedulingService()


# Default user and calendar IDs (hardcoded for simplicity)
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_CALENDAR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class EventRepository:
    """Repository for event database operations."""
    
    def __init__(self, db: AsyncSession, timezone: str = "Asia/Bangkok", user_id: Optional[uuid.UUID] = None):
        self.db = db
        self.timezone = timezone
        self.user_id = user_id or DEFAULT_USER_ID
        try:
            self.tz = ZoneInfo(timezone)
        except Exception:
            self.tz = ZoneInfo("Asia/Bangkok")
    
    async def get_calendar_id(self) -> uuid.UUID:
        """Get the calendar for the current user."""
        # Try to find a calendar for this user
        result = await self.db.execute(
            select(Calendar).where(Calendar.user_id == self.user_id).limit(1)
        )
        calendar = result.scalar_one_or_none()
        
        if calendar:
            return calendar.id
        
        # Fallback to default calendar
        result = await self.db.execute(
            select(Calendar).where(Calendar.id == DEFAULT_CALENDAR_ID)
        )
        calendar = result.scalar_one_or_none()
        
        if calendar:
            return calendar.id
        
        return DEFAULT_CALENDAR_ID
    
    async def get_events_on_date(
        self,
        day: int,
        month: int,
        year: int,
        calendar_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all events on a specific date.
        
        Returns events in a format suitable for Prolog processing.
        """
        if calendar_id is None:
            calendar_id = await self.get_calendar_id()
        
        # Create datetime range for the day
        start_of_day = datetime(year, month, day, 0, 0, 0, tzinfo=self.tz)
        end_of_day = datetime(year, month, day, 23, 59, 59, tzinfo=self.tz)
        
        result = await self.db.execute(
            select(Event).where(
                and_(
                    or_(
                        Event.calendar_id == calendar_id,
                        Event.id.in_(
                            select(EventCollaborator.event_id)
                            .where(EventCollaborator.user_id == self.user_id)
                        ),
                    ),
                    Event.status == "confirmed",
                    Event.start_time < end_of_day,
                    Event.end_time > start_of_day,
                )
            ).order_by(Event.start_time)
        )
        events = result.scalars().all()
        
        return [self._event_to_dict(e) for e in events]
    
    async def get_events_in_date_range(
        self,
        start_day: int,
        start_month: int,
        start_year: int,
        end_day: int,
        end_month: int,
        end_year: int,
        calendar_id: Optional[uuid.UUID] = None
    ) -> Dict[Tuple[int, int, int], List[Dict[str, Any]]]:
        """
        Get events grouped by date within a range.
        
        Returns a dict mapping (day, month, year) to list of events.
        """
        if calendar_id is None:
            calendar_id = await self.get_calendar_id()
        
        start_date = datetime(start_year, start_month, start_day, 0, 0, 0, tzinfo=self.tz)
        end_date = datetime(end_year, end_month, end_day, 23, 59, 59, tzinfo=self.tz)
        
        result = await self.db.execute(
            select(Event).where(
                and_(
                    or_(
                        Event.calendar_id == calendar_id,
                        Event.id.in_(
                            select(EventCollaborator.event_id)
                            .where(EventCollaborator.user_id == self.user_id)
                        ),
                    ),
                    Event.status == "confirmed",
                    Event.start_time < end_date,
                    Event.end_time > start_date,
                )
            ).order_by(Event.start_time)
        )
        events = result.scalars().all()
        
        # Group by date
        events_by_date: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
        
        # Initialize empty lists for each day in range
        current = start_date
        while current <= end_date:
            key = (current.day, current.month, current.year)
            events_by_date[key] = []
            current += timedelta(days=1)
        
        # Add events to their respective days
        for event in events:
            event_dict = self._event_to_dict(event)
            local_start = event.start_time.astimezone(self.tz)
            key = (local_start.day, local_start.month, local_start.year)
            if key in events_by_date:
                events_by_date[key].append(event_dict)
        
        return events_by_date
    
    async def get_events_for_week(
        self,
        reference_day: int,
        reference_month: int,
        reference_year: int,
        calendar_id: Optional[uuid.UUID] = None
    ) -> Dict[Tuple[int, int, int], List[Dict[str, Any]]]:
        """Get events for 7 days starting from the reference date."""
        end_date = datetime(reference_year, reference_month, reference_day) + timedelta(days=6)
        return await self.get_events_in_date_range(
            reference_day, reference_month, reference_year,
            end_date.day, end_date.month, end_date.year,
            calendar_id
        )
    
    async def create_event(
        self,
        title: str,
        day: int,
        month: int,
        year: int,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int,
        location: Optional[str] = None,
        notes: Optional[str] = None,
        calendar_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Create a new event.
        
        Returns the created event data.
        """
        if calendar_id is None:
            calendar_id = await self.get_calendar_id()
        
        start_time = datetime(year, month, day, start_hour, start_minute, 0, tzinfo=self.tz)
        end_time = datetime(year, month, day, end_hour, end_minute, 0, tzinfo=self.tz)
        
        event = Event(
            calendar_id=calendar_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            location=location,
            notes=notes,
            status="confirmed",
        )
        
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        
        return self._event_to_dict(event)
    
    async def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        day: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        start_hour: Optional[int] = None,
        start_minute: Optional[int] = None,
        end_hour: Optional[int] = None,
        end_minute: Optional[int] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing event.
        
        Returns the updated event data or None if not found.
        """
        try:
            event_uuid = uuid.UUID(event_id)
        except ValueError:
            return None
        
        result = await self.db.execute(
            select(Event).where(Event.id == event_uuid)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            return None
        
        if title is not None:
            event.title = title
        if location is not None:
            event.location = location
        if notes is not None:
            event.notes = notes
        
        # Update time if any time component is provided
        if any(x is not None for x in [day, month, year, start_hour, start_minute, end_hour, end_minute]):
            local_start = event.start_time.astimezone(self.tz)
            local_end = event.end_time.astimezone(self.tz)
            
            new_day = day if day is not None else local_start.day
            new_month = month if month is not None else local_start.month
            new_year = year if year is not None else local_start.year
            new_start_hour = start_hour if start_hour is not None else local_start.hour
            new_start_minute = start_minute if start_minute is not None else local_start.minute
            new_end_hour = end_hour if end_hour is not None else local_end.hour
            new_end_minute = end_minute if end_minute is not None else local_end.minute
            
            event.start_time = datetime(
                new_year, new_month, new_day, 
                new_start_hour, new_start_minute, 0, 
                tzinfo=self.tz
            )
            event.end_time = datetime(
                new_year, new_month, new_day,
                new_end_hour, new_end_minute, 0,
                tzinfo=self.tz
            )
        
        await self.db.flush()
        await self.db.refresh(event)
        
        return self._event_to_dict(event)
    
    async def delete_event(self, event_id: str) -> bool:
        """
        Delete an event (soft delete - marks as cancelled).
        
        Returns True if deleted, False if not found.
        """
        try:
            event_uuid = uuid.UUID(event_id)
        except ValueError:
            return False
        
        result = await self.db.execute(
            select(Event).where(Event.id == event_uuid)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            return False
        
        event.status = "cancelled"
        await self.db.flush()
        
        return True
    
    async def find_event_by_title_and_date(
        self,
        title: str,
        day: int,
        month: int,
        year: int,
        calendar_id: Optional[uuid.UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find an event by title on a specific date.
        
        Returns the event data or None if not found.
        """
        if calendar_id is None:
            calendar_id = await self.get_calendar_id()
        
        start_of_day = datetime(year, month, day, 0, 0, 0, tzinfo=self.tz)
        end_of_day = datetime(year, month, day, 23, 59, 59, tzinfo=self.tz)
        
        result = await self.db.execute(
            select(Event).where(
                and_(
                    or_(
                        Event.calendar_id == calendar_id,
                        Event.id.in_(
                            select(EventCollaborator.event_id)
                            .where(EventCollaborator.user_id == self.user_id)
                        ),
                    ),
                    Event.status == "confirmed",
                    Event.title.ilike(f"%{title}%"),
                    Event.start_time >= start_of_day,
                    Event.start_time <= end_of_day,
                )
            )
        )
        event = result.scalar_one_or_none()
        
        if not event:
            return None
        
        return self._event_to_dict(event)
    
    async def get_events_for_query(
        self,
        query_type: str,
        day: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        calendar_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get events based on query type (day, week, month).
        
        Returns list of events formatted for display.
        """
        if calendar_id is None:
            calendar_id = await self.get_calendar_id()
        
        now = datetime.now(self.tz)
        
        if query_type == "day":
            d = day if day else now.day
            m = month if month else now.month
            y = year if year else now.year
            return await self.get_events_on_date(d, m, y, calendar_id)
        
        elif query_type == "week":
            d = day if day else now.day
            m = month if month else now.month
            y = year if year else now.year
            events_by_day = await self.get_events_for_week(d, m, y, calendar_id)
            # Flatten to list
            all_events = []
            for events in events_by_day.values():
                all_events.extend(events)
            return all_events
        
        elif query_type == "month":
            m = month if month else now.month
            y = year if year else now.year
            # Get first and last day of month
            first_day = datetime(y, m, 1, tzinfo=self.tz)
            if m == 12:
                last_day = datetime(y + 1, 1, 1, tzinfo=self.tz) - timedelta(days=1)
            else:
                last_day = datetime(y, m + 1, 1, tzinfo=self.tz) - timedelta(days=1)
            
            events_by_day = await self.get_events_in_date_range(
                1, m, y, last_day.day, m, y, calendar_id
            )
            all_events = []
            for events in events_by_day.values():
                all_events.extend(events)
            return all_events
        
        return []
    
    async def get_user_priority_map(self, user_id: Optional[uuid.UUID] = None) -> Dict[str, int]:
        """
        Get the user's event-type priority mapping from their profile.
        
        Returns merged priorities (extracted + defaults).
        Falls back to default weights if no profile exists.
        """
        uid = user_id or self.user_id
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == uid)
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            return profile.merge_priorities()
        
        # Fallback default priorities
        return {
            "meeting": 7, "exam": 10, "study": 8, "deadline": 10,
            "appointment": 7, "class": 8, "work": 8, "exercise": 5,
            "social": 4, "party": 3, "personal": 5, "travel": 6, "other": 5,
        }
    
    def _event_to_dict(self, event: Event) -> Dict[str, Any]:
        """Convert Event model to dictionary format for Prolog/chat."""
        local_start = event.start_time.astimezone(self.tz)
        local_end = event.end_time.astimezone(self.tz)

        # Infer event type and priority from the title so that the constraint
        # solver can use them even when no priority_map is available.
        event_type = _svc._infer_event_type(event.title or "")
        priority = _svc.default_priorities.get(event_type, 5)

        return {
            "id": str(event.id),
            "title": event.title,
            "day": local_start.day,
            "month": local_start.month,
            "year": local_start.year,
            "start_hour": local_start.hour,
            "start_minute": local_start.minute,
            "end_hour": local_end.hour,
            "end_minute": local_end.minute,
            "location": event.location,
            "notes": event.notes,
            "status": event.status,
            "event_type": event_type,
            "priority": priority,
        }
