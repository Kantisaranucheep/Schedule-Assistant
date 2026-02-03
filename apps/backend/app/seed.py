# schedule-assistant/apps/backend/app/seed.py
"""Seed script to create demo data."""

import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_maker
from app.models.user import User
from app.models.calendar import Calendar
from app.models.event_type import EventType
from app.models.user_settings import UserSettings


async def seed_database() -> None:
    """
    Seed the database with demo data.

    Creates:
    - Demo user (demo@example.com)
    - Default calendar (Personal)
    - Event types: Meeting, Class, Gym

    This function is idempotent - safe to run multiple times.
    """
    async with async_session_maker() as db:
        # Check if demo user already exists
        result = await db.execute(
            select(User).where(User.email == "demo@example.com")
        )
        user = result.scalar_one_or_none()

        if user:
            print("Demo user already exists, skipping user creation...")
        else:
            # Create demo user
            user = User(
                name="Demo User",
                email="demo@example.com",
            )
            db.add(user)
            await db.flush()
            print(f"Created demo user: {user.email} (ID: {user.id})")

        # Check/create user settings
        settings = await db.get(UserSettings, user.id)
        if not settings:
            settings = UserSettings(
                user_id=user.id,
                timezone="Asia/Bangkok",
                default_duration_min=60,
                buffer_min=10,
                preferences={
                    "working_hours_start": "09:00",
                    "working_hours_end": "18:00",
                },
            )
            db.add(settings)
            await db.flush()
            print("Created user settings")

        # Check/create default calendar
        result = await db.execute(
            select(Calendar).where(
                Calendar.user_id == user.id,
                Calendar.name == "Personal",
            )
        )
        calendar = result.scalar_one_or_none()

        if not calendar:
            calendar = Calendar(
                user_id=user.id,
                name="Personal",
                timezone="Asia/Bangkok",
            )
            db.add(calendar)
            await db.flush()
            print(f"Created calendar: {calendar.name} (ID: {calendar.id})")
        else:
            print("Default calendar already exists, skipping...")

        # Event types to create
        event_types_data = [
            {"name": "Meeting", "color": "#3B82F6", "default_duration_min": 60},
            {"name": "Class", "color": "#10B981", "default_duration_min": 90},
            {"name": "Gym", "color": "#F59E0B", "default_duration_min": 60},
        ]

        for et_data in event_types_data:
            # Check if event type already exists
            result = await db.execute(
                select(EventType).where(
                    EventType.user_id == user.id,
                    EventType.name == et_data["name"],
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                event_type = EventType(
                    user_id=user.id,
                    name=et_data["name"],
                    color=et_data["color"],
                    default_duration_min=et_data["default_duration_min"],
                )
                db.add(event_type)
                print(f"Created event type: {et_data['name']}")
            else:
                print(f"Event type '{et_data['name']}' already exists, skipping...")

        await db.commit()
        print("\nSeed completed successfully!")
        print(f"\nDemo user ID: {user.id}")
        print("You can use this ID for API requests.")


def main() -> None:
    """Run the seed script."""
    print("Starting database seed...")
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
