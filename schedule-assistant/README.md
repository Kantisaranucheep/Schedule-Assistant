# Schedule Assistant

A monorepo project for a Schedule Assistant application with AI-powered scheduling capabilities.

## Project Structure

```
schedule-assistant/
├── apps/
│   ├── frontend/          # Next.js frontend (placeholder)
│   └── backend/           # FastAPI backend
│       ├── app/
│       │   ├── core/      # Config, database setup
│       │   ├── models/    # SQLAlchemy ORM models
│       │   ├── schemas/   # Pydantic schemas
│       │   ├── routers/   # API endpoints
│       │   └── services/  # Business logic
│       └── alembic/       # Database migrations
├── packages/
│   └── db/                # Shared database utilities
├── docker/                # Docker configuration
└── docs/                  # Documentation
```

## Tech Stack

- **Frontend**: Next.js (placeholder)
- **Backend**: FastAPI + Uvicorn
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy 2.0 (async with asyncpg)
- **Migrations**: Alembic
- **Validation**: Pydantic v2

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for frontend)

## Getting Started

### 1. Start PostgreSQL Database

```bash
cd docker
docker compose up -d
```

This will start PostgreSQL on port 5432 with persistent volume.

### 2. Setup Backend

```bash
cd apps/backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.\.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example env file (from repo root)
cp .env.example .env

# Edit .env if needed (defaults work with docker-compose)
```

### 4. Run Database Migrations

```bash
cd apps/backend
alembic upgrade head
```

### 5. Seed Demo Data

```bash
cd apps/backend
python -m app.seed
```

This creates:
- Demo user (demo@example.com)
- Default calendar (Personal)
- Event types: Meeting, Class, Gym

### 6. Start Backend Server

```bash
cd apps/backend
uvicorn app.main:app --reload --port 8000
```

### 7. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/calendars` | List calendars for user |
| POST | `/calendars` | Create calendar |
| GET | `/events` | List events (with date range) |
| POST | `/events` | Create event |
| PUT | `/events/{id}` | Update event |
| DELETE | `/events/{id}` | Delete event |
| GET | `/availability` | Get free time slots |
| POST | `/chat/sessions` | Create chat session |
| GET | `/chat/sessions` | List chat sessions |
| GET | `/chat/sessions/{id}/messages` | Get messages |
| POST | `/chat/sessions/{id}/messages` | Add message |
| GET | `/settings` | Get user settings |
| PUT | `/settings` | Update user settings |

## Development

### Running Tests

```bash
cd apps/backend
pytest
```

### Creating New Migration

```bash
cd apps/backend
alembic revision --autogenerate -m "Description of changes"
```

### Stopping Services

```bash
cd docker
docker compose down
```

To also remove the database volume:
```bash
docker compose down -v
```

## License

MIT
