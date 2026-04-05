"""Database seeding script for demo data."""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import User, UserSettings, Calendar, Event, Category


# Fixed UUIDs for demo data
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_CALENDAR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Default categories matching frontend
DEFAULT_CATEGORIES = [
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000101"), "name": "Urgent / Important", "color": "#ff3b30"},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000102"), "name": "Work", "color": "#ff9500"},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000103"), "name": "Personal", "color": "#ffcc00"},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000104"), "name": "Health / Fitness", "color": "#34c759"},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000105"), "name": "Reminder", "color": "#00c7be"},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000106"), "name": "Meetings / Appointments", "color": "#007aff"},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000107"), "name": "Social / Fun", "color": "#af52de"},
]


async def seed_database():
    """Seed database with demo data."""
    async with AsyncSessionLocal() as db:
        # Check if demo user already exists
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == DEMO_USER_ID))
        if result.scalar_one_or_none():
            print("Demo user already exists, skipping seed.")
            return

        # Create demo user
        demo_user = User(
            id=DEMO_USER_ID,
            email="demo@example.com",
            name="Demo User",
            timezone="Asia/Bangkok",
        )
        db.add(demo_user)

        # Create user settings
        user_settings = UserSettings(
            user_id=DEMO_USER_ID,
            working_hours_start="09:00",
            working_hours_end="18:00",
            buffer_minutes=10,
        )
        db.add(user_settings)

        # Create default calendar
        demo_calendar = Calendar(
            id=DEMO_CALENDAR_ID,
            user_id=DEMO_USER_ID,
            name="My Calendar",
            color="#3B82F6",
            timezone="Asia/Bangkok",
        )
        db.add(demo_calendar)

        # Create default categories for the calendar
        for cat_data in DEFAULT_CATEGORIES:
            category = Category(
                id=cat_data["id"],
                calendar_id=DEMO_CALENDAR_ID,
                name=cat_data["name"],
                color=cat_data["color"],
            )
            db.add(category)

        await db.commit()

        print("=" * 50)
        print("Demo data seeded successfully!")
        print("=" * 50)
        print(f"Demo User ID:     {DEMO_USER_ID}")
        print(f"Demo Calendar ID: {DEMO_CALENDAR_ID}")
        print(f"Demo Email:       demo@example.com")
        print(f"Categories:       {len(DEFAULT_CATEGORIES)} default categories created")
        print("=" * 50)


def main():
    """Entry point for seeding."""
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
