"""Task CRUD endpoints."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import TaskCreate, TaskUpdate, TaskResponse
from app.services import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    calendar_id: UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get tasks for a calendar."""
    service = TaskService(db)
    return await service.get_by_calendar(calendar_id, start_date, end_date)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific task."""
    service = TaskService(db)
    task = await service.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new task."""
    service = TaskService(db)
    return await service.create(data)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a task."""
    service = TaskService(db)
    task = await service.update(task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark a task as completed."""
    service = TaskService(db)
    task = await service.complete(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    soft: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task (soft delete by default)."""
    service = TaskService(db)
    deleted = await service.delete(task_id, soft=soft)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
