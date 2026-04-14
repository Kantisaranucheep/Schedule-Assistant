"""Event service - CRUD operations with conflict detection."""

from datetime import datetime, timezone as dt_timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, User, Calendar, EventCollaborator, EventCollaborationInvitation
from app.schemas import EventCreate, EventUpdate
from app.core.websockets import manager


def ensure_timezone_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware. If naive, assume UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=dt_timezone.utc)
    return dt


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
        # Find user_id of calendar owner via a quick DB query
        q = await self.db.execute(select(Calendar).where(Calendar.id == calendar_id))
        calendar = q.scalar_one_or_none()
        user_id = calendar.user_id if calendar else None

        if user_id:
            query = select(Event).where(
                and_(
                    or_(
                        Event.calendar_id == calendar_id,
                        Event.id.in_(
                            select(EventCollaborator.event_id)
                            .where(EventCollaborator.user_id == user_id)
                        )
                    ),
                    Event.status != "cancelled"
                )
            )
        else:
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
        """Create a new event with timezone-aware datetimes."""
        
        # 1. Validate usernames
        usernames = data.collaborator_usernames or []
        invitees = []
        if usernames:
            user_q = await self.db.execute(select(User).where(User.username.in_(usernames)))
            found_users = user_q.scalars().all()
            found_usernames = {u.username for u in found_users}
            missing = [un for un in usernames if un not in found_usernames]
            if missing:
                # Fast fail, trigger 400
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=f"Users not found: {', '.join(missing)}")
            invitees = found_users

        # 2. Extract calendar owner as inviter
        q = await self.db.execute(select(Calendar).where(Calendar.id == data.calendar_id))
        calendar = q.scalar_one_or_none()
        inviter_id = calendar.user_id if calendar else None
            
        event_data = data.model_dump(exclude={"timezone", "collaborator_usernames"})
        
        # Ensure datetimes are timezone-aware
        event_data["start_time"] = ensure_timezone_aware(event_data["start_time"])
        event_data["end_time"] = ensure_timezone_aware(event_data["end_time"])
        
        event = Event(**event_data)
        self.db.add(event)
        await self.db.flush()
        
        # 3. Create invitations
        if invitees and inviter_id:
            for invitee in invitees:
                invitation = EventCollaborationInvitation(
                    event_id=event.id,
                    inviter_id=inviter_id,
                    invitee_id=invitee.id
                )
                self.db.add(invitation)
                # 4. Fire WebSocket
                await manager.send_personal_message({"type": "new_invitation"}, invitee.id)
                
        await self.db.refresh(event)
        return event

    async def update(self, event_id: UUID, data: EventUpdate) -> Optional[Event]:
        """Update an event."""
        event = await self.get(event_id)
        if not event:
            return None

        # 1. Validate usernames
        usernames = data.collaborator_usernames or []
        invitees = []
        if usernames:
            user_q = await self.db.execute(select(User).where(User.username.in_(usernames)))
            found_users = user_q.scalars().all()
            found_usernames = {u.username for u in found_users}
            missing = [un for un in usernames if un not in found_usernames]
            if missing:
                # Fast fail, trigger 400
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=f"Users not found: {', '.join(missing)}")
            invitees = found_users

        update_data = data.model_dump(exclude_unset=True, exclude={"collaborator_usernames"})
        for field, value in update_data.items():
            setattr(event, field, value)

        await self.db.flush()

        # 2. Extract calendar owner as inviter
        if invitees:
            q = await self.db.execute(select(Calendar).where(Calendar.id == event.calendar_id))
            calendar = q.scalar_one_or_none()
            inviter_id = calendar.user_id if calendar else None
            if inviter_id:
                # Get existing invitations for this event
                inv_q = await self.db.execute(
                    select(EventCollaborationInvitation.invitee_id)
                    .where(EventCollaborationInvitation.event_id == event.id)
                )
                existing_invitee_ids = set(inv_q.scalars().all())

                for invitee in invitees:
                    if invitee.id not in existing_invitee_ids:
                        invitation = EventCollaborationInvitation(
                            event_id=event.id,
                            inviter_id=inviter_id,
                            invitee_id=invitee.id
                        )
                        self.db.add(invitation)
                        # Fire WebSocket
                        await manager.send_personal_message({"type": "new_invitation"}, invitee.id)

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
