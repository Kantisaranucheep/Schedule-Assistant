# Schedule Assistant - Backend

FastAPI backend for the Schedule Assistant application.

This guide is Docker-only. Use it to bring up the full backend stack, apply database migrations, load demo data, and pull the Ollama model.

## Tech Stack

- FastAPI
- Uvicorn
- SQLAlchemy 2.0 async
- asyncpg
- Alembic
- Pydantic v2

---

## Docker Setup

### Prerequisites

1. Install Docker Desktop: https://www.docker.com/products/docker-desktop
2. Start Docker Desktop and wait until it is fully running

### 1. Start the stack

From the repository root:

```powershell
cd docker
docker-compose up -d postgres backend ollama
```

Wait about 30 seconds for the containers to become healthy.

### 2. Apply migrations

```powershell
docker exec -it schedule-assistant-api alembic upgrade head
```

This creates and updates the database schema, including categories and tasks.

### 3. Seed demo data

```powershell
docker exec -it schedule-assistant-api python -m app.seed
```

The seed script is idempotent. If the demo user already exists, it will still create any missing calendar, settings, and default categories.

Windows fallback if you need to run the seed file directly on the host:

```powershell
python E:\1_Work\SE-Year3\SS2\KRR\project_GitVersion\Schedule-Assistant\apps\backend\app\seed.py
```

### 4. Pull the Ollama model

```powershell
docker exec -it schedule-assistant-ollama ollama pull llama3.2
```

### 5. Verify the setup

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Agent health: http://localhost:8000/agent/health
- Ollama API: http://localhost:11434

---

## One-shot Bootstrap

If you already started the containers, run these commands in order:

```powershell
docker exec -it schedule-assistant-api alembic upgrade head
docker exec -it schedule-assistant-api python -m app.seed
docker exec -it schedule-assistant-ollama ollama pull llama3.2
```

---

## Useful Docker Commands

```powershell
# Check container status
docker ps

# View backend logs
docker logs schedule-assistant-api -f

# View database logs
docker logs schedule-assistant-db -f

# View Ollama logs
docker logs schedule-assistant-ollama -f

# List Ollama models
docker exec -it schedule-assistant-ollama ollama list

# Stop the stack
cd docker
docker-compose down

# Stop and remove all data
docker-compose down -v

# Rebuild the backend container after code changes
docker-compose up -d --build backend
```

---

## Demo Data

After seeding, the database contains:

- Demo user: `demo@example.com`
- Demo calendar
- Default categories:
	- Urgent / Important
	- Work
	- Personal
	- Health / Fitness
	- Reminder
	- Meetings / Appointments
	- Social / Fun

---

## Environment Variables

The backend container already sets these values in `docker-compose.yml`:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@postgres:5432/schedule_assistant` |
| `APP_NAME` | `Schedule Assistant` |
| `DEBUG` | `true` |
| `SECRET_KEY` | `docker-secret-key-change-in-production` |
| `CORS_ORIGINS` | `http://localhost:3000` |
| `DEFAULT_TIMEZONE` | `Asia/Bangkok` |
| `AGENT_LLM_PROVIDER` | `ollama` |
| `OLLAMA_BASE_URL` | `http://ollama:11434` |
| `OLLAMA_MODEL` | `llama3.2` |
| `PROLOG_MODE` | `subprocess` |
| `PROLOG_PATH` | `/app/prolog` |

---

## Troubleshooting

### Docker daemon not running

**Error**: `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`

**Fix**: Start Docker Desktop and wait until it is fully running.

### Port already in use

**Error**: `Bind for 0.0.0.0:5433 failed: port is already allocated`

**Fix**:

```powershell
netstat -ano | findstr :5433
docker-compose down
docker-compose up -d postgres backend ollama
```

### Database tables do not exist

**Error**: `relation "users" does not exist`

**Fix**:

```powershell
docker exec -it schedule-assistant-api alembic upgrade head
```

### Categories are missing

**Fix**: Rerun the seed command:

```powershell
docker exec -it schedule-assistant-api python -m app.seed
```

### Ollama model is missing

**Fix**:

```powershell
docker exec -it schedule-assistant-ollama ollama pull llama3.2
docker exec -it schedule-assistant-ollama ollama list
```

### Container keeps restarting

**Fix**: Check logs.

```powershell
docker logs schedule-assistant-api
docker logs schedule-assistant-db
docker logs schedule-assistant-ollama
```

### Reset everything

```powershell
cd docker
docker-compose down -v
docker-compose up -d postgres backend ollama
docker exec -it schedule-assistant-api alembic upgrade head
docker exec -it schedule-assistant-api python -m app.seed
docker exec -it schedule-assistant-ollama ollama pull llama3.2
```

---

## API Endpoints

- `GET /health` - backend health
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc
- `GET /agent/health` - Ollama/agent health

---

## Notes

- The backend seed script now fills in missing data instead of stopping when the demo user already exists.
- Use Docker commands from the repository root unless the step explicitly says otherwise.
