"""Category service - CRUD operations."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category
from app.schemas import CategoryCreate, CategoryUpdate


class CategoryService:
    """Category CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, category_id: UUID) -> Optional[Category]:
        """Get category by ID."""
        result = await self.db.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()

    async def get_by_calendar(self, calendar_id: UUID) -> List[Category]:
        """Get all categories for a calendar."""
        query = select(Category).where(Category.calendar_id == calendar_id).order_by(Category.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_name(self, calendar_id: UUID, name: str) -> Optional[Category]:
        """Get category by name within a calendar."""
        result = await self.db.execute(
            select(Category).where(
                and_(
                    Category.calendar_id == calendar_id,
                    Category.name.ilike(name)
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: CategoryCreate) -> Category:
        """Create a new category."""
        category = Category(**data.model_dump())
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def update(self, category_id: UUID, data: CategoryUpdate) -> Optional[Category]:
        """Update a category."""
        category = await self.get(category_id)
        if not category:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)

        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def delete(self, category_id: UUID) -> bool:
        """Delete a category."""
        category = await self.get(category_id)
        if not category:
            return False

        await self.db.delete(category)
        await self.db.flush()
        return True

    async def create_default_categories(self, calendar_id: UUID) -> List[Category]:
        """Create default categories for a new calendar."""
        default_categories = [
            {"name": "Urgent / Important", "color": "#ff3b30"},
            {"name": "Work", "color": "#ff9500"},
            {"name": "Personal", "color": "#ffcc00"},
            {"name": "Health / Fitness", "color": "#34c759"},
            {"name": "Reminder", "color": "#00c7be"},
            {"name": "Meetings / Appointments", "color": "#007aff"},
            {"name": "Social / Fun", "color": "#af52de"},
        ]

        categories = []
        for cat_data in default_categories:
            category = Category(calendar_id=calendar_id, **cat_data)
            self.db.add(category)
            categories.append(category)

        await self.db.flush()
        for cat in categories:
            await self.db.refresh(cat)

        return categories
