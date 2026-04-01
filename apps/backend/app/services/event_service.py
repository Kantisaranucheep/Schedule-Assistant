"""Event service - CRUD operations with conflict detection."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event
from app.schemas import EventCreate, EventUpdate


class EventService:
    """Event CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, event_id: UUID) -> Optional[Event]:
        """Get event by ID."""
        result = await self.db.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    async def get_by_calendar(
        self,
        calendar_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Event]:
        """Get events for a calendar, optionally filtered by date range."""
        query = select(Event).where(
            and_(Event.calendar_id == calendar_id, Event.status != "cancelled")
        )

        if start_date:
            query = query.where(Event.end_time >= start_date)
        if end_date:
            query = query.where(Event.start_time <= end_date)

        query = query.order_by(Event.start_time)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def check_conflicts(
        self,
        calendar_id: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_event_id: Optional[UUID] = None,
    ) -> List[Event]:
        """Find overlapping events."""
        query = select(Event).where(
            and_(
                Event.calendar_id == calendar_id,
                Event.status == "confirmed",
                Event.start_time < end_time,
                Event.end_time > start_time,
            )
        )

        if exclude_event_id:
            query = query.where(Event.id != exclude_event_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, data: EventCreate) -> Event:
        """Create a new event."""
        event = Event(**data.model_dump())
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def update(self, event_id: UUID, data: EventUpdate) -> Optional[Event]:
        """Update an event."""
        event = await self.get(event_id)
        if not event:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)

        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def delete(self, event_id: UUID, soft: bool = True) -> bool:
        """Delete an event. Soft delete marks as cancelled."""
        event = await self.get(event_id)
        if not event:
            return False

        if soft:
            event.status = "cancelled"
            await self.db.flush()
        else:
            await self.db.delete(event)
            await self.db.flush()

        return True

    async def find_by_title_and_date(
        self, calendar_id: UUID, title: str, date: datetime
    ) -> Optional[Event]:
        """Find event by title on a specific date."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        result = await self.db.execute(
            select(Event).where(
                and_(
                    Event.calendar_id == calendar_id,
                    Event.title.ilike(f"%{title}%"),
                    Event.start_time >= start_of_day,
                    Event.start_time <= end_of_day,
                    Event.status != "cancelled",
                )
            )
        )
        return result.scalar_one_or_none()
