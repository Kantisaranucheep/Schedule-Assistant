# apps/backend/app/services/event_service.py
"""Unified event service - handles CRUD with Prolog validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.calendar import Calendar
from app.services.conflicts import check_event_conflicts
from app.integrations.prolog_client import get_prolog_client


class EventService:
    """Service for event operations with integrated Prolog validation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._prolog_client = None

    @property
    def prolog(self):
        """Lazy load prolog client."""
        if self._prolog_client is None:
            self._prolog_client = get_prolog_client()
        return self._prolog_client

    async def create_event(
        self,
        calendar_id: UUID,
        title: str,
        start_at: datetime,
        end_at: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        created_by: str = "agent",
        skip_validation: bool = False,
    ) -> Dict[str, Any]:
        """Create event with Prolog validation.
        
        Args:
            calendar_id: Target calendar UUID
            title: Event title
            start_at: Start datetime
            end_at: End datetime
            description: Optional description
            location: Optional location
            created_by: 'user' or 'agent'
            skip_validation: Skip Prolog validation
            
        Returns:
            Dict with success status, event data or error
        """
        # Verify calendar exists
        calendar = await self.db.get(Calendar, calendar_id)
        if not calendar:
            return {
                "success": False,
                "error": f"Calendar {calendar_id} not found"
            }

        # Validate with Prolog (check conflicts and working hours)
        if not skip_validation:
            validation = await self._validate_with_prolog(
                calendar_id, start_at, end_at
            )
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["reason"],
                    "conflicts": validation.get("conflicts", []),
                    "prolog_validation": validation
                }

        # Check for conflicts in database
        conflicts = await check_event_conflicts(
            db=self.db,
            calendar_id=calendar_id,
            start_at=start_at,
            end_at=end_at,
        )
        if conflicts:
            return {
                "success": False,
                "error": "Event conflicts with existing events",
                "conflicts": [{"id": str(e.id), "title": e.title} for e in conflicts]
            }

        # Create event
        event = Event(
            calendar_id=calendar_id,
            title=title,
            description=description,
            location=location,
            start_at=start_at,
            end_at=end_at,
            status="confirmed",
            created_by=created_by,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        await self.db.commit()

        return {
            "success": True,
            "event": {
                "id": str(event.id),
                "title": event.title,
                "start_at": event.start_at.isoformat(),
                "end_at": event.end_at.isoformat(),
                "location": event.location,
                "description": event.description,
                "status": event.status,
            },
            "message": f"Event '{title}' created successfully"
        }

    async def update_event(
        self,
        event_id: UUID,
        title: Optional[str] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update event with Prolog validation.
        
        Args:
            event_id: Event UUID to update
            Other args: Fields to update (None = no change)
            
        Returns:
            Dict with success status, updated event data or error
        """
        event = await self.db.get(Event, event_id)
        if not event:
            return {
                "success": False,
                "error": f"Event {event_id} not found"
            }

        # Determine new times
        new_start = start_at if start_at is not None else event.start_at
        new_end = end_at if end_at is not None else event.end_at

        if new_end <= new_start:
            return {
                "success": False,
                "error": "End time must be after start time"
            }

        # Validate with Prolog if times changed
        if start_at is not None or end_at is not None:
            validation = await self._validate_with_prolog(
                event.calendar_id, new_start, new_end, exclude_event_id=event_id
            )
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["reason"],
                    "conflicts": validation.get("conflicts", []),
                    "prolog_validation": validation
                }

            # Check DB conflicts
            conflicts = await check_event_conflicts(
                db=self.db,
                calendar_id=event.calendar_id,
                start_at=new_start,
                end_at=new_end,
                exclude_event_id=event_id,
            )
            if conflicts:
                return {
                    "success": False,
                    "error": "Event conflicts with existing events",
                    "conflicts": [{"id": str(e.id), "title": e.title} for e in conflicts]
                }

        # Update fields
        if title is not None:
            event.title = title
        if start_at is not None:
            event.start_at = start_at
        if end_at is not None:
            event.end_at = end_at
        if description is not None:
            event.description = description
        if location is not None:
            event.location = location

        event.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(event)

        return {
            "success": True,
            "event": {
                "id": str(event.id),
                "title": event.title,
                "start_at": event.start_at.isoformat(),
                "end_at": event.end_at.isoformat(),
                "location": event.location,
                "description": event.description,
                "status": event.status,
            },
            "message": f"Event '{event.title}' updated successfully"
        }

    async def delete_event(
        self,
        event_id: Optional[UUID] = None,
        title: Optional[str] = None,
        calendar_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Delete event by ID or by title (within calendar).
        
        Args:
            event_id: Event UUID (preferred)
            title: Event title (fallback, requires calendar_id)
            calendar_id: Calendar UUID (required if using title)
            
        Returns:
            Dict with success status
        """
        event = None

        if event_id:
            event = await self.db.get(Event, event_id)
        elif title and calendar_id:
            result = await self.db.execute(
                select(Event).where(
                    Event.calendar_id == calendar_id,
                    Event.title == title,
                    Event.status != "cancelled"
                ).order_by(Event.start_at.desc()).limit(1)
            )
            event = result.scalar_one_or_none()

        if not event:
            return {
                "success": False,
                "error": "Event not found"
            }

        event_title = event.title
        await self.db.delete(event)

        return {
            "success": True,
            "message": f"Event '{event_title}' deleted successfully"
        }

    async def get_events(
        self,
        calendar_id: UUID,
        start_from: Optional[datetime] = None,
        end_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get events for a calendar within optional date range.
        
        Args:
            calendar_id: Calendar UUID
            start_from: Optional start datetime filter
            end_to: Optional end datetime filter
            
        Returns:
            Dict with events list
        """
        query = select(Event).where(
            Event.calendar_id == calendar_id,
            Event.status != "cancelled"
        )

        if start_from:
            query = query.where(Event.start_at >= start_from)
        if end_to:
            query = query.where(Event.end_at <= end_to)

        query = query.order_by(Event.start_at)
        result = await self.db.execute(query)
        events = result.scalars().all()

        return {
            "success": True,
            "events": [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "start_at": e.start_at.isoformat(),
                    "end_at": e.end_at.isoformat(),
                    "location": e.location,
                    "description": e.description,
                    "status": e.status,
                }
                for e in events
            ]
        }

    async def find_event(
        self,
        calendar_id: UUID,
        title: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find event by title and/or date.
        
        Args:
            calendar_id: Calendar UUID
            title: Event title to search
            date: Date string (YYYY-MM-DD)
            
        Returns:
            Dict with matching event or error
        """
        query = select(Event).where(
            Event.calendar_id == calendar_id,
            Event.status != "cancelled"
        )

        if title:
            query = query.where(Event.title.ilike(f"%{title}%"))

        if date:
            date_start = datetime.strptime(date, "%Y-%m-%d")
            date_end = datetime.strptime(date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.where(Event.start_at >= date_start, Event.start_at <= date_end)

        query = query.order_by(Event.start_at).limit(1)
        result = await self.db.execute(query)
        event = result.scalar_one_or_none()

        if not event:
            return {
                "success": False,
                "error": "Event not found"
            }

        return {
            "success": True,
            "event": {
                "id": str(event.id),
                "title": event.title,
                "start_at": event.start_at.isoformat(),
                "end_at": event.end_at.isoformat(),
                "location": event.location,
                "description": event.description,
                "status": event.status,
            }
        }

    async def _validate_with_prolog(
        self,
        calendar_id: UUID,
        start_at: datetime,
        end_at: datetime,
        exclude_event_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Validate event with Prolog rules.
        
        Checks:
        - No overlapping events
        - Within working hours (if configured)
        
        Returns:
            Dict with validation result
        """
        try:
            # Build Prolog query for conflict check
            query = f"api_check_overlap('{calendar_id}', '{start_at.isoformat()}', '{end_at.isoformat()}', Result)"
            result = await self.prolog.query(query)

            if isinstance(result, dict):
                if result.get("has_conflicts", False):
                    conflicts = result.get("conflict_ids", [])
                    # Filter out the event being updated
                    if exclude_event_id:
                        conflicts = [c for c in conflicts if c != str(exclude_event_id)]
                    if conflicts:
                        return {
                            "valid": False,
                            "reason": "overlap",
                            "conflicts": conflicts
                        }

            return {"valid": True, "reason": "ok"}

        except Exception as e:
            # If Prolog fails, log but don't block (fallback to DB check)
            return {
                "valid": True,
                "reason": "prolog_unavailable",
                "note": str(e)
            }
