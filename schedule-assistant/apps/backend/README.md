# Schedule Assistant - Backend

FastAPI backend for the Schedule Assistant application.

## Tech Stack

- **Framework**: FastAPI
- **Server**: Uvicorn
- **ORM**: SQLAlchemy 2.0 (async)
- **Database Driver**: asyncpg
- **Migrations**: Alembic
- **Validation**: Pydantic v2

## Project Structure

```
app/
├── main.py              # FastAPI application entry point
├── core/
│   ├── config.py        # Settings and configuration
│   └── db.py            # Database connection setup
├── models/              # SQLAlchemy ORM models
│   ├── user.py
│   ├── calendar.py
│   ├── event_type.py
│   ├── event.py
│   ├── user_settings.py
│   ├── chat_session.py
│   └── chat_message.py
├── schemas/             # Pydantic request/response schemas
│   ├── user.py
│   ├── calendar.py
│   ├── event_type.py
│   ├── event.py
│   ├── chat.py
│   └── settings.py
├── routers/             # API endpoints
│   ├── health.py
│   ├── calendars.py
│   ├── events.py
│   ├── chat.py
│   └── settings.py
├── services/            # Business logic
│   ├── availability.py
│   └── conflicts.py
└── seed.py              # Database seeding script
```

## Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the repo root (or copy from `.env.example`):

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/schedule_assistant
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Seed Database

```bash
python -m app.seed
```

### 6. Run Server

```bash
uvicorn app.main:app --reload --port 8000
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Database Migrations

### Create a new migration

```bash
alembic revision --autogenerate -m "Description"
```

### Apply migrations

```bash
alembic upgrade head
```

### Rollback

```bash
alembic downgrade -1
```

## Testing

```bash
pytest
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/schedule_assistant` |
| `APP_NAME` | Application name | `Schedule Assistant` |
| `DEBUG` | Enable debug mode | `true` |
| `SECRET_KEY` | Secret key for security | `change-me-in-production` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `DEFAULT_TIMEZONE` | Default timezone | `Asia/Bangkok` |
| `DEFAULT_WORKING_HOURS_START` | Working hours start | `09:00` |
| `DEFAULT_WORKING_HOURS_END` | Working hours end | `18:00` |
