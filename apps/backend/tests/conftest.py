"""
Test fixtures and configuration for Schedule Assistant backend tests.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models import Calendar, Category, Event, Task, User, UserSettings


# Use SQLite for testing (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing."""
    
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# ============ Sample Data Fixtures ============

@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Create a sample user for testing."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        timezone="Asia/Bangkok",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_calendar(db_session: AsyncSession, sample_user: User) -> Calendar:
    """Create a sample calendar for testing."""
    calendar = Calendar(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        name="Test Calendar",
        color="#3498db",
        timezone="Asia/Bangkok",
    )
    db_session.add(calendar)
    await db_session.flush()
    await db_session.refresh(calendar)
    return calendar


@pytest_asyncio.fixture
async def sample_category(db_session: AsyncSession, sample_calendar: Calendar) -> Category:
    """Create a sample category for testing."""
    category = Category(
        id=uuid.uuid4(),
        calendar_id=sample_calendar.id,
        name="Work",
        color="#e74c3c",
    )
    db_session.add(category)
    await db_session.flush()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def sample_event(db_session: AsyncSession, sample_calendar: Calendar, sample_category: Category) -> Event:
    """Create a sample event for testing."""
    now = datetime.now(timezone.utc)
    event = Event(
        id=uuid.uuid4(),
        calendar_id=sample_calendar.id,
        title="Team Meeting",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        all_day=False,
        location="Conference Room A",
        notes="Weekly team sync",
        category_id=sample_category.id,
        status="confirmed",
    )
    db_session.add(event)
    await db_session.flush()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def sample_task(db_session: AsyncSession, sample_calendar: Calendar, sample_category: Category) -> Task:
    """Create a sample task for testing."""
    task = Task(
        id=uuid.uuid4(),
        calendar_id=sample_calendar.id,
        title="Complete project report",
        date=datetime.now(timezone.utc).date(),
        location="Office",
        notes="Submit by EOD",
        category_id=sample_category.id,
        status="pending",
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task


# ============ Helper Functions ============

def create_event_data(calendar_id: uuid.UUID, **kwargs) -> dict:
    """Create event data dictionary for API testing."""
    now = datetime.now(timezone.utc)
    default_data = {
        "calendar_id": str(calendar_id),
        "title": "Test Event",
        "start_time": (now + timedelta(hours=1)).isoformat(),
        "end_time": (now + timedelta(hours=2)).isoformat(),
        "all_day": False,
        "location": "Test Location",
        "notes": "Test notes",
    }
    default_data.update(kwargs)
    return default_data


def create_task_data(calendar_id: uuid.UUID, **kwargs) -> dict:
    """Create task data dictionary for API testing."""
    default_data = {
        "calendar_id": str(calendar_id),
        "title": "Test Task",
        "date": datetime.now(timezone.utc).date().isoformat(),
        "location": "Test Location",
        "notes": "Test notes",
    }
    default_data.update(kwargs)
    return default_data
