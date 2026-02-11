# Schedule Assistant - Backend

FastAPI backend for the Schedule Assistant application.

## Tech Stack

- **Framework**: FastAPI
- **Server**: Uvicorn
- **ORM**: SQLAlchemy 2.0 (async)
- **Database Driver**: asyncpg
- **Migrations**: Alembic
- **Validation**: Pydantic v2

---

## 🚀 Quick Start (Docker - Recommended)

This is the easiest way to get started. Everything runs in Docker containers.

### Prerequisites

1. **Install Docker Desktop**: https://www.docker.com/products/docker-desktop
2. **Start Docker Desktop** and wait until it's fully running (green icon in system tray)

### Step-by-Step Setup

#### Step 1: Clone the repository
```bash
git clone <repository-url>
cd Schedule-Assistant
```

#### Step 2: Start the containers
```powershell
# Navigate to docker folder
cd docker

# Start PostgreSQL and Backend
docker-compose up -d postgres backend
```

Wait for containers to be healthy (about 30 seconds).

#### Step 3: Run database migrations
```powershell
docker exec -it schedule-assistant-api alembic upgrade head
```

#### Step 4: Seed demo data
```powershell
docker exec -it schedule-assistant-api python -m app.seed
```

#### Step 5: Verify it's working
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 🎉 Done! 

The backend is now running with:
- **API**: http://localhost:8000
- **PostgreSQL**: localhost:5433 (Docker container)

### Demo Credentials
After seeding, you'll get a demo user ID. Use it for API requests:
- **User Email**: `demo@example.com`

---

## 🛠️ Useful Docker Commands

```powershell
# Check container status
docker ps

# View backend logs
docker logs schedule-assistant-api -f

# View database logs
docker logs schedule-assistant-db -f

# Stop all containers
cd docker
docker-compose down

# Restart containers
docker-compose restart

# Rebuild backend after code changes
docker-compose up -d --build backend

# Access database CLI
docker exec -it schedule-assistant-db psql -U postgres -d schedule_assistant

# Run a specific SQL query
docker exec -it schedule-assistant-db psql -U postgres -d schedule_assistant -c "SELECT * FROM users;"
```

---

## 🗄️ View Database in pgAdmin (Optional)

If you have pgAdmin installed and want to browse the database:

1. Open pgAdmin
2. Right-click **Servers** → **Register** → **Server...**
3. Fill in:

| Tab | Field | Value |
|-----|-------|-------|
| General | Name | `Schedule Assistant (Docker)` |
| Connection | Host | `localhost` |
| Connection | Port | `5433` |
| Connection | Database | `schedule_assistant` |
| Connection | Username | `postgres` |
| Connection | Password | `postgres` |

4. Click **Save**

---

## 💻 Local Development (Without Docker)

If you prefer running Python directly on your machine:

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ (local or Docker)

### Step 1: Start PostgreSQL (via Docker)
```powershell
cd docker
docker-compose up -d postgres
```

### Step 2: Setup Python environment
```powershell
cd apps/backend

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Create .env file
Create `apps/backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/schedule_assistant
APP_NAME=Schedule Assistant
DEBUG=true
SECRET_KEY=dev-secret-key
CORS_ORIGINS=http://localhost:3000
DEFAULT_TIMEZONE=Asia/Bangkok
```

### Step 4: Run migrations and seed
```powershell
alembic upgrade head
python -m app.seed
```

### Step 5: Start the server
```powershell
uvicorn app.main:app --reload --port 8000
```

---

## 📁 Project Structure

```
app/
├── main.py              # FastAPI application entry point
├── core/
│   ├── config.py        # Settings and configuration
│   └── db.py            # Database connection setup
├── models/              # SQLAlchemy ORM models (database tables)
│   ├── user.py
│   ├── calendar.py
│   ├── event.py
│   ├── event_type.py
│   ├── user_settings.py
│   ├── chat_session.py
│   └── chat_message.py
├── schemas/             # Pydantic schemas (API request/response)
│   ├── user.py
│   ├── calendar.py
│   ├── event.py
│   ├── event_type.py
│   ├── chat.py
│   └── settings.py
├── routers/             # API endpoints
│   ├── health.py        # Health check
│   ├── calendars.py     # Calendar CRUD
│   ├── events.py        # Event CRUD
│   ├── chat.py          # Chat sessions
│   ├── settings.py      # User settings
│   └── agent.py         # AI Agent endpoints
├── services/            # Business logic
│   ├── availability.py  # Find available time slots
│   └── conflicts.py     # Detect scheduling conflicts
├── agent/               # AI Intent processing
│   ├── parser.py        # Parse user text → Intent
│   ├── executor.py      # Execute Intent → Action
│   ├── schemas.py       # Intent data models
│   └── llm_clients.py   # LLM client abstraction
├── integrations/
│   └── prolog_client.py # Prolog integration
└── seed.py              # Database seeding script
```

---

## 📖 API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔄 Database Migrations

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

---

## ⚠️ Troubleshooting

### Docker daemon not running
**Error**: `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`

**Solution**: Start Docker Desktop from Windows Start Menu and wait until it's fully running.

---

### Port already in use
**Error**: `Bind for 0.0.0.0:5433 failed: port is already allocated`

**Solution**: 
```powershell
# Check what's using the port
netstat -ano | findstr :5433

# Stop all containers and restart
docker-compose down
docker-compose up -d postgres backend
```

---

### Database tables don't exist
**Error**: `relation "users" does not exist`

**Solution**: Run migrations first:
```powershell
docker exec -it schedule-assistant-api alembic upgrade head
```

---

### Container keeps restarting
**Solution**: Check the logs:
```powershell
docker logs schedule-assistant-api
docker logs schedule-assistant-db
```

---

### Reset everything (fresh start)
```powershell
cd docker

# Stop and remove containers + volumes
docker-compose down -v

# Rebuild and start fresh
docker-compose up -d --build postgres backend

# Wait 30 seconds, then run migrations
docker exec -it schedule-assistant-api alembic upgrade head
docker exec -it schedule-assistant-api python -m app.seed
```

---

## 🧪 Testing the API

### Quick test endpoints

```powershell
# Health check
curl http://localhost:8000/health

# Get API info
curl http://localhost:8000/

# Check agent health
curl http://localhost:8000/agent/health
```

### Test with Swagger UI
Open http://localhost:8000/docs in your browser and use the interactive API documentation.
