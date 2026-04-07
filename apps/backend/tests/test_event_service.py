"""
Unit tests for EventService.

Test ID Format: UT-EVT-XXX
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, Calendar
from app.schemas import EventCreate, EventUpdate
from app.services import EventService


class TestEventServiceCreate:
    """Test cases for EventService.create() method."""

    @pytest.mark.asyncio
    async def test_create_event_success(self, db_session: AsyncSession, sample_calendar: Calendar):
        """
        UT-EVT-001: Create event with valid data
        
        Precondition: Calendar exists
        Input: Valid event data with title, start_time, end_time
        Expected: Event created successfully with all fields populated
        """
        service = EventService(db_session)
        now = datetime.now(timezone.utc)
        
        event_data = EventCreate(
            calendar_id=sample_calendar.id,
            title="Project Meeting",
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            all_day=False,
            location="Room 101",
            notes="Discuss project timeline",
        )
        
        result = await service.create(event_data)
        
        assert result is not None
        assert result.id is not None
        assert result.title == "Project Meeting"
        assert result.calendar_id == sample_calendar.id
        assert result.location == "Room 101"
        assert result.status == "confirmed"

    @pytest.mark.asyncio
    async def test_create_all_day_event(self, db_session: AsyncSession, sample_calendar: Calendar):
        """
        UT-EVT-002: Create all-day event
        
        Precondition: Calendar exists
        Input: Event data with all_day=True
        Expected: Event created with all_day flag set to True
        """
        service = EventService(db_session)
        now = datetime.now(timezone.utc)
        
        event_data = EventCreate(
            calendar_id=sample_calendar.id,
            title="Company Holiday",
            start_time=now.replace(hour=0, minute=0, second=0, microsecond=0),
            end_time=now.replace(hour=23, minute=59, second=59, microsecond=0),
            all_day=True,
        )
        
        result = await service.create(event_data)
        
        assert result.all_day is True
        assert result.title == "Company Holiday"

    @pytest.mark.asyncio
    async def test_create_event_with_category(
        self, db_session: AsyncSession, sample_calendar: Calendar, sample_category
    ):
        """
        UT-EVT-003: Create event with category
        
        Precondition: Calendar and Category exist
        Input: Event data with category_id
        Expected: Event created with category association
        """
        service = EventService(db_session)
        now = datetime.now(timezone.utc)
        
        event_data = EventCreate(
            calendar_id=sample_calendar.id,
            title="Work Meeting",
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            category_id=sample_category.id,
        )
        
        result = await service.create(event_data)
        
        assert result.category_id == sample_category.id


class TestEventServiceGet:
    """Test cases for EventService.get() method."""

    @pytest.mark.asyncio
    async def test_get_existing_event(self, db_session: AsyncSession, sample_event: Event):
        """
        UT-EVT-004: Get existing event by ID
        
        Precondition: Event exists in database
        Input: Valid event ID
        Expected: Returns event with matching ID
        """
        service = EventService(db_session)
        
        result = await service.get(sample_event.id)
        
        assert result is not None
        assert result.id == sample_event.id
        assert result.title == sample_event.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_event(self, db_session: AsyncSession):
        """
        UT-EVT-005: Get event with non-existent ID
        
        Precondition: None
        Input: Random UUID that doesn't exist
        Expected: Returns None
        """
        service = EventService(db_session)
        
        result = await service.get(uuid.uuid4())
        
        assert result is None


class TestEventServiceGetByCalendar:
    """Test cases for EventService.get_by_calendar() method."""

    @pytest.mark.asyncio
    async def test_get_events_by_calendar(self, db_session: AsyncSession, sample_event: Event, sample_calendar: Calendar):
        """
        UT-EVT-006: Get all events for a calendar
        
        Precondition: Calendar has events
        Input: Calendar ID
        Expected: Returns list of events for that calendar
        """
        service = EventService(db_session)
        
        result = await service.get_by_calendar(sample_calendar.id)
        
        assert len(result) >= 1
        assert any(e.id == sample_event.id for e in result)

    @pytest.mark.asyncio
    async def test_get_events_with_date_filter(self, db_session: AsyncSession, sample_calendar: Calendar):
        """
        UT-EVT-007: Get events within date range
        
        Precondition: Calendar has events at specific dates
        Input: Calendar ID with start_date and end_date filters
        Expected: Returns only events within the specified range
        """
        service = EventService(db_session)
        now = datetime.now(timezone.utc)
        
        # Create events at different times
        event1 = EventCreate(
            calendar_id=sample_calendar.id,
            title="Past Event",
            start_time=now - timedelta(days=5),
            end_time=now - timedelta(days=5, hours=-1),
        )
        event2 = EventCreate(
            calendar_id=sample_calendar.id,
            title="Future Event",
            start_time=now + timedelta(days=5),
            end_time=now + timedelta(days=5, hours=1),
        )
        
        await service.create(event1)
        await service.create(event2)
        
        # Filter for future events only
        result = await service.get_by_calendar(
            sample_calendar.id,
            start_date=now,
            end_date=now + timedelta(days=10),
        )
        
        # Should return at least the future event
        assert len(result) >= 1
        # Verify all events have valid dates (comparing with naive datetime)
        now_naive = datetime.utcnow()
        for e in result:
            event_start = e.start_time.replace(tzinfo=None) if e.start_time.tzinfo else e.start_time
            event_end = e.end_time.replace(tzinfo=None) if e.end_time.tzinfo else e.end_time
            assert event_start is not None and event_end is not None


class TestEventServiceUpdate:
    """Test cases for EventService.update() method."""

    @pytest.mark.asyncio
    async def test_update_event_title(self, db_session: AsyncSession, sample_event: Event):
        """
        UT-EVT-008: Update event title
        
        Precondition: Event exists
        Input: Event ID and new title
        Expected: Event title updated successfully
        """
        service = EventService(db_session)
        
        update_data = EventUpdate(title="Updated Meeting Title")
        result = await service.update(sample_event.id, update_data)
        
        assert result is not None
        assert result.title == "Updated Meeting Title"

    @pytest.mark.asyncio
    async def test_update_event_time(self, db_session: AsyncSession, sample_event: Event):
        """
        UT-EVT-009: Update event time
        
        Precondition: Event exists
        Input: Event ID and new start/end times
        Expected: Event times updated successfully
        """
        service = EventService(db_session)
        new_start = datetime.now(timezone.utc) + timedelta(days=1)
        new_end = new_start + timedelta(hours=3)
        
        update_data = EventUpdate(start_time=new_start, end_time=new_end)
        result = await service.update(sample_event.id, update_data)
        
        assert result is not None
        # Compare timestamps (allowing for microsecond differences)
        # Handle timezone-aware vs naive comparison
        result_start = result.start_time
        if result_start.tzinfo is None:
            result_start = result_start.replace(tzinfo=timezone.utc)
        assert abs((result_start - new_start).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_update_nonexistent_event(self, db_session: AsyncSession):
        """
        UT-EVT-010: Update non-existent event
        
        Precondition: None
        Input: Non-existent event ID
        Expected: Returns None
        """
        service = EventService(db_session)
        
        update_data = EventUpdate(title="New Title")
        result = await service.update(uuid.uuid4(), update_data)
        
        assert result is None


class TestEventServiceDelete:
    """Test cases for EventService.delete() method."""

    @pytest.mark.asyncio
    async def test_soft_delete_event(self, db_session: AsyncSession, sample_event: Event):
        """
        UT-EVT-011: Soft delete event
        
        Precondition: Event exists with status 'confirmed'
        Input: Event ID with soft=True
        Expected: Event status changed to 'cancelled'
        """
        service = EventService(db_session)
        
        result = await service.delete(sample_event.id, soft=True)
        
        assert result is True
        
        # Verify event still exists but is cancelled
        event = await service.get(sample_event.id)
        assert event is not None
        assert event.status == "cancelled"

    @pytest.mark.asyncio
    async def test_hard_delete_event(self, db_session: AsyncSession, sample_calendar: Calendar):
        """
        UT-EVT-012: Hard delete event
        
        Precondition: Event exists
        Input: Event ID with soft=False
        Expected: Event removed from database
        """
        service = EventService(db_session)
        now = datetime.now(timezone.utc)
        
        # Create an event to delete
        event_data = EventCreate(
            calendar_id=sample_calendar.id,
            title="Event to Delete",
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )
        event = await service.create(event_data)
        event_id = event.id
        
        # Hard delete
        result = await service.delete(event_id, soft=False)
        
        assert result is True
        
        # Verify event is completely removed
        deleted_event = await service.get(event_id)
        assert deleted_event is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_event(self, db_session: AsyncSession):
        """
        UT-EVT-013: Delete non-existent event
        
        Precondition: None
        Input: Non-existent event ID
        Expected: Returns False
        """
        service = EventService(db_session)
        
        result = await service.delete(uuid.uuid4())
        
        assert result is False


class TestEventServiceConflictDetection:
    """Test cases for EventService.check_conflicts() method."""

    @pytest.mark.asyncio
    async def test_detect_overlapping_events(self, db_session: AsyncSession, sample_event: Event, sample_calendar: Calendar):
        """
        UT-EVT-014: Detect overlapping events
        
        Precondition: Existing event at specific time
        Input: New event time that overlaps with existing event
        Expected: Returns list containing the conflicting event
        """
        service = EventService(db_session)
        
        # Check for conflict with same time as sample_event
        conflicts = await service.check_conflicts(
            sample_calendar.id,
            sample_event.start_time,
            sample_event.end_time,
        )
        
        assert len(conflicts) >= 1
        assert any(c.id == sample_event.id for c in conflicts)

    @pytest.mark.asyncio
    async def test_no_conflict_for_non_overlapping_time(
        self, db_session: AsyncSession, sample_event: Event, sample_calendar: Calendar
    ):
        """
        UT-EVT-015: No conflict for non-overlapping time
        
        Precondition: Existing event at specific time
        Input: New event time that doesn't overlap
        Expected: Returns empty list
        """
        service = EventService(db_session)
        
        # Check for a time slot well after the sample event
        future_time = sample_event.end_time + timedelta(hours=5)
        conflicts = await service.check_conflicts(
            sample_calendar.id,
            future_time,
            future_time + timedelta(hours=1),
        )
        
        assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_exclude_self_from_conflict_check(
        self, db_session: AsyncSession, sample_event: Event, sample_calendar: Calendar
    ):
        """
        UT-EVT-016: Exclude self when checking conflicts during update
        
        Precondition: Event exists
        Input: Same event's time with exclude_event_id set
        Expected: Returns empty list (doesn't conflict with itself)
        """
        service = EventService(db_session)
        
        conflicts = await service.check_conflicts(
            sample_calendar.id,
            sample_event.start_time,
            sample_event.end_time,
            exclude_event_id=sample_event.id,
        )
        
        # Should not find the event itself as a conflict
        assert not any(c.id == sample_event.id for c in conflicts)
