"""Task service - CRUD operations."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task
from app.schemas import TaskCreate, TaskUpdate


class TaskService:
    """Task CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID."""
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def get_by_calendar(
        self,
        calendar_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Task]:
        """Get tasks for a calendar, optionally filtered by date range."""
        query = select(Task).where(
            and_(Task.calendar_id == calendar_id, Task.status != "cancelled")
        )

        if start_date:
            query = query.where(Task.date >= start_date)
        if end_date:
            query = query.where(Task.date <= end_date)

        query = query.order_by(Task.date)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_date(self, calendar_id: UUID, task_date: date) -> List[Task]:
        """Get tasks for a specific date."""
        query = select(Task).where(
            and_(
                Task.calendar_id == calendar_id,
                Task.date == task_date,
                Task.status != "cancelled"
            )
        ).order_by(Task.created_at)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, data: TaskCreate) -> Task:
        """Create a new task."""
        task = Task(**data.model_dump())
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def update(self, task_id: UUID, data: TaskUpdate) -> Optional[Task]:
        """Update a task."""
        task = await self.get(task_id)
        if not task:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def delete(self, task_id: UUID, soft: bool = True) -> bool:
        """Delete a task. Soft delete marks as cancelled."""
        task = await self.get(task_id)
        if not task:
            return False

        if soft:
            task.status = "cancelled"
            await self.db.flush()
        else:
            await self.db.delete(task)
            await self.db.flush()

        return True

    async def complete(self, task_id: UUID) -> Optional[Task]:
        """Mark a task as completed."""
        task = await self.get(task_id)
        if not task:
            return None

        task.status = "completed"
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def find_by_title_and_date(
        self, calendar_id: UUID, title: str, task_date: date
    ) -> Optional[Task]:
        """Find task by title on a specific date."""
        result = await self.db.execute(
            select(Task).where(
                and_(
                    Task.calendar_id == calendar_id,
                    Task.title.ilike(f"%{title}%"),
                    Task.date == task_date,
                    Task.status != "cancelled",
                )
            )
        )
        return result.scalar_one_or_none()
