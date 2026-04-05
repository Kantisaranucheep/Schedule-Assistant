"""Category CRUD endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import CategoryCreate, CategoryUpdate, CategoryResponse
from app.services import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=List[CategoryResponse])
async def list_categories(
    calendar_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all categories for a calendar."""
    service = CategoryService(db)
    return await service.get_by_calendar(calendar_id)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific category."""
    service = CategoryService(db)
    category = await service.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new category."""
    service = CategoryService(db)
    return await service.create(data)


@router.post("/defaults", response_model=List[CategoryResponse], status_code=201)
async def create_default_categories(
    calendar_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Create default categories for a calendar."""
    service = CategoryService(db)
    return await service.create_default_categories(calendar_id)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a category."""
    service = CategoryService(db)
    category = await service.update(category_id, data)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a category."""
    service = CategoryService(db)
    deleted = await service.delete(category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
