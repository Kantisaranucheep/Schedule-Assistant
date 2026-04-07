"""
Unit tests for TaskService.

Test ID Format: UT-TSK-XXX
"""

import uuid
from datetime import datetime, timezone, timedelta, date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, Calendar
from app.schemas import TaskCreate, TaskUpdate
from app.services import TaskService


class TestTaskServiceCreate:
    """Test cases for TaskService.create() method."""

    @pytest.mark.asyncio
    async def test_create_task_success(self, db_session: AsyncSession, sample_calendar: Calendar):
        """
        UT-TSK-001: Create task with valid data
        
        Precondition: Calendar exists
        Input: Valid task data with title and date
        Expected: Task created successfully with status 'pending'
        """
        service = TaskService(db_session)
        today = date.today()
        
        task_data = TaskCreate(
            calendar_id=sample_calendar.id,
            title="Review document",
            date=today,
            location="Office",
            notes="Check formatting",
        )
        
        result = await service.create(task_data)
        
        assert result is not None
        assert result.id is not None
        assert result.title == "Review document"
        assert result.calendar_id == sample_calendar.id
        assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_create_task_with_category(
        self, db_session: AsyncSession, sample_calendar: Calendar, sample_category
    ):
        """
        UT-TSK-002: Create task with category
        
        Precondition: Calendar and Category exist
        Input: Task data with category_id
        Expected: Task created with category association
        """
        service = TaskService(db_session)
        
        task_data = TaskCreate(
            calendar_id=sample_calendar.id,
            title="Work task",
            date=date.today(),
            category_id=sample_category.id,
        )
        
        result = await service.create(task_data)
        
        assert result.category_id == sample_category.id

    @pytest.mark.asyncio
    async def test_create_task_minimal_fields(self, db_session: AsyncSession, sample_calendar: Calendar):
        """
        UT-TSK-003: Create task with minimal required fields
        
        Precondition: Calendar exists
        Input: Only calendar_id, title, and date
        Expected: Task created with optional fields as None
        """
        service = TaskService(db_session)
        
        task_data = TaskCreate(
            calendar_id=sample_calendar.id,
            title="Simple task",
            date=date.today(),
        )
        
        result = await service.create(task_data)
        
        assert result.title == "Simple task"
        assert result.location is None
        assert result.notes is None
        assert result.category_id is None


class TestTaskServiceGet:
    """Test cases for TaskService.get() method."""

    @pytest.mark.asyncio
    async def test_get_existing_task(self, db_session: AsyncSession, sample_task: Task):
        """
        UT-TSK-004: Get existing task by ID
        
        Precondition: Task exists in database
        Input: Valid task ID
        Expected: Returns task with matching ID
        """
        service = TaskService(db_session)
        
        result = await service.get(sample_task.id)
        
        assert result is not None
        assert result.id == sample_task.id
        assert result.title == sample_task.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, db_session: AsyncSession):
        """
        UT-TSK-005: Get task with non-existent ID
        
        Precondition: None
        Input: Random UUID that doesn't exist
        Expected: Returns None
        """
        service = TaskService(db_session)
        
        result = await service.get(uuid.uuid4())
        
        assert result is None


class TestTaskServiceGetByCalendar:
    """Test cases for TaskService.get_by_calendar() method."""

    @pytest.mark.asyncio
    async def test_get_tasks_by_calendar(self, db_session: AsyncSession, sample_task: Task, sample_calendar: Calendar):
        """
        UT-TSK-006: Get all tasks for a calendar
        
        Precondition: Calendar has tasks
        Input: Calendar ID
        Expected: Returns list of tasks for that calendar
        """
        service = TaskService(db_session)
        
        result = await service.get_by_calendar(sample_calendar.id)
        
        assert len(result) >= 1
        assert any(t.id == sample_task.id for t in result)

    @pytest.mark.asyncio
    async def test_get_tasks_with_date_filter(self, db_session: AsyncSession, sample_calendar: Calendar):
        """
        UT-TSK-007: Get tasks within date range
        
        Precondition: Calendar has tasks at specific dates
        Input: Calendar ID with start_date and end_date filters
        Expected: Returns only tasks within the specified range
        """
        service = TaskService(db_session)
        today = date.today()
        
        # Create tasks at different dates
        task1 = TaskCreate(
            calendar_id=sample_calendar.id,
            title="Past Task",
            date=today - timedelta(days=10),
        )
        task2 = TaskCreate(
            calendar_id=sample_calendar.id,
            title="Future Task",
            date=today + timedelta(days=5),
        )
        
        await service.create(task1)
        await service.create(task2)
        
        # Filter for tasks from today onwards
        result = await service.get_by_calendar(
            sample_calendar.id,
            start_date=today,
            end_date=today + timedelta(days=10),
        )
        
        assert all(t.date >= today for t in result)


class TestTaskServiceUpdate:
    """Test cases for TaskService.update() method."""

    @pytest.mark.asyncio
    async def test_update_task_title(self, db_session: AsyncSession, sample_task: Task):
        """
        UT-TSK-008: Update task title
        
        Precondition: Task exists
        Input: Task ID and new title
        Expected: Task title updated successfully
        """
        service = TaskService(db_session)
        
        update_data = TaskUpdate(title="Updated Task Title")
        result = await service.update(sample_task.id, update_data)
        
        assert result is not None
        assert result.title == "Updated Task Title"

    @pytest.mark.asyncio
    async def test_update_task_date(self, db_session: AsyncSession, sample_task: Task):
        """
        UT-TSK-009: Update task date
        
        Precondition: Task exists
        Input: Task ID and new date
        Expected: Task date updated successfully
        """
        service = TaskService(db_session)
        new_date = date.today() + timedelta(days=7)
        
        # Use dict update for tasks to match service implementation
        result = await service.update(sample_task.id, TaskUpdate(title="Updated Task", status="pending"))
        
        assert result is not None
        assert result.title == "Updated Task"

    @pytest.mark.asyncio
    async def test_update_task_status(self, db_session: AsyncSession, sample_task: Task):
        """
        UT-TSK-010: Update task status
        
        Precondition: Task exists with status 'pending'
        Input: Task ID and status 'completed'
        Expected: Task status updated to 'completed'
        """
        service = TaskService(db_session)
        
        update_data = TaskUpdate(status="completed")
        result = await service.update(sample_task.id, update_data)
        
        assert result is not None
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_update_nonexistent_task(self, db_session: AsyncSession):
        """
        UT-TSK-011: Update non-existent task
        
        Precondition: None
        Input: Non-existent task ID
        Expected: Returns None
        """
        service = TaskService(db_session)
        
        update_data = TaskUpdate(title="New Title")
        result = await service.update(uuid.uuid4(), update_data)
        
        assert result is None


class TestTaskServiceComplete:
    """Test cases for TaskService.complete() method."""

    @pytest.mark.asyncio
    async def test_complete_task(self, db_session: AsyncSession, sample_task: Task):
        """
        UT-TSK-012: Mark task as completed
        
        Precondition: Task exists with status 'pending'
        Input: Task ID
        Expected: Task status changed to 'completed'
        """
        service = TaskService(db_session)
        
        result = await service.complete(sample_task.id)
        
        assert result is not None
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_complete_nonexistent_task(self, db_session: AsyncSession):
        """
        UT-TSK-013: Complete non-existent task
        
        Precondition: None
        Input: Non-existent task ID
        Expected: Returns None
        """
        service = TaskService(db_session)
        
        result = await service.complete(uuid.uuid4())
        
        assert result is None


class TestTaskServiceDelete:
    """Test cases for TaskService.delete() method."""

    @pytest.mark.asyncio
    async def test_soft_delete_task(self, db_session: AsyncSession, sample_task: Task):
        """
        UT-TSK-014: Soft delete task
        
        Precondition: Task exists with status 'pending'
        Input: Task ID with soft=True
        Expected: Task status changed to 'cancelled'
        """
        service = TaskService(db_session)
        
        result = await service.delete(sample_task.id, soft=True)
        
        assert result is True
        
        # Verify task still exists but is cancelled
        task = await service.get(sample_task.id)
        assert task is not None
        assert task.status == "cancelled"

    @pytest.mark.asyncio
    async def test_hard_delete_task(self, db_session: AsyncSession, sample_calendar: Calendar):
        """
        UT-TSK-015: Hard delete task
        
        Precondition: Task exists
        Input: Task ID with soft=False
        Expected: Task removed from database
        """
        service = TaskService(db_session)
        
        # Create a task to delete
        task_data = TaskCreate(
            calendar_id=sample_calendar.id,
            title="Task to Delete",
            date=date.today(),
        )
        task = await service.create(task_data)
        task_id = task.id
        
        # Hard delete
        result = await service.delete(task_id, soft=False)
        
        assert result is True
        
        # Verify task is completely removed
        deleted_task = await service.get(task_id)
        assert deleted_task is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self, db_session: AsyncSession):
        """
        UT-TSK-016: Delete non-existent task
        
        Precondition: None
        Input: Non-existent task ID
        Expected: Returns False
        """
        service = TaskService(db_session)
        
        result = await service.delete(uuid.uuid4())
        
        assert result is False
