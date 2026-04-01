"""Calendar service - CRUD operations."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Calendar
from app.schemas import CalendarCreate, CalendarUpdate


class CalendarService:
    """Calendar CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, calendar_id: UUID) -> Optional[Calendar]:
        """Get calendar by ID."""
        result = await self.db.execute(select(Calendar).where(Calendar.id == calendar_id))
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID) -> List[Calendar]:
        """Get all calendars for a user."""
        result = await self.db.execute(
            select(Calendar).where(Calendar.user_id == user_id).order_by(Calendar.name)
        )
        return list(result.scalars().all())

    async def create(self, data: CalendarCreate) -> Calendar:
        """Create a new calendar."""
        calendar = Calendar(**data.model_dump())
        self.db.add(calendar)
        await self.db.flush()
        await self.db.refresh(calendar)
        return calendar

    async def update(self, calendar_id: UUID, data: CalendarUpdate) -> Optional[Calendar]:
        """Update a calendar."""
        calendar = await self.get(calendar_id)
        if not calendar:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(calendar, field, value)

        await self.db.flush()
        await self.db.refresh(calendar)
        return calendar

    async def delete(self, calendar_id: UUID) -> bool:
        """Delete a calendar."""
        calendar = await self.get(calendar_id)
        if not calendar:
            return False

        await self.db.delete(calendar)
        await self.db.flush()
        return True
