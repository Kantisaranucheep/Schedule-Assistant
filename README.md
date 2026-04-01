# Schedule Assistant

An AI-powered scheduling assistant with natural language processing for calendar management.

---

## 🚀 Quick Start (Docker - Recommended)

### Prerequisites

1. **Docker Desktop**: https://www.docker.com/products/docker-desktop
2. **Node.js 18+**: https://nodejs.org/
3. **Git**: https://git-scm.com/

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Schedule-Assistant
```

### Step 2: Start Database, Backend & LLM (Docker)

```bash
cd docker
docker-compose up -d postgres backend ollama
```

Wait ~30 seconds for containers to be healthy.

### Step 3: Run Database Migrations

```bash
docker exec -it schedule-assistant-api alembic upgrade head
```

### Step 4: Seed Demo Data

```bash
docker exec -it schedule-assistant-api python -m app.seed
```

### Step 5: Pull the LLM Model (First Time Only)

```bash
docker exec -it schedule-assistant-ollama ollama pull llama3.2
```

### Step 6: Start Frontend

```bash
cd apps/frontend/frontend
npm install
npm run dev
```

### 🎉 Done!

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/health |

---

## 📁 Project Structure

```
Schedule-Assistant/
├── apps/
│   ├── frontend/           # Next.js frontend
│   │   └── frontend/
│   │       ├── app/        # React components & pages
│   │       └── package.json
│   ├── backend/            # FastAPI backend
│   │   ├── app/
│   │   │   ├── agent/      # LLM intent parsing & execution
│   │   │   ├── core/       # Config, database setup
│   │   │   ├── models/     # SQLAlchemy ORM models
│   │   │   ├── schemas/    # Pydantic schemas
│   │   │   ├── routers/    # API endpoints
│   │   │   ├── services/   # Business logic
│   │   │   └── integrations/ # Prolog client
│   │   └── alembic/        # Database migrations
│   └── prolog/             # Constraint logic (scheduling rules)
├── docker/                 # Docker Compose configuration
└── docs/                   # Documentation
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Uvicorn, Python 3.11 |
| **Database** | PostgreSQL 16, SQLAlchemy 2.0 (async) |
| **LLM** | Ollama (llama3.2), optional Gemini |
| **Constraint Logic** | SWI-Prolog |
| **Migrations** | Alembic |

---

## 📖 API Endpoints

### Chat (Main Endpoint)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent/chat` | Send message to AI assistant |
| GET | `/agent/health` | Check LLM availability |

### Calendars
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/calendars?user_id=` | List user calendars |
| POST | `/calendars` | Create calendar |
| GET | `/calendars/{id}` | Get calendar |
| PATCH | `/calendars/{id}` | Update calendar |
| DELETE | `/calendars/{id}` | Delete calendar |

### Events
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/events?calendar_id=` | List events |
| POST | `/events` | Create event |
| GET | `/events/{id}` | Get event |
| PATCH | `/events/{id}` | Update event |
| DELETE | `/events/{id}` | Delete event |
| GET | `/events/conflicts/check` | Check for conflicts |

### Availability
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/availability/free-slots` | Find free time slots |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/settings/{user_id}` | Get user settings |
| POST | `/settings` | Create settings |
| PATCH | `/settings/{user_id}` | Update settings |

---

## 🐳 Docker Commands

```bash
# Start all services
cd docker
docker-compose up -d postgres backend ollama

# Check container status
docker ps

# View logs
docker logs schedule-assistant-api -f
docker logs schedule-assistant-ollama -f
docker logs schedule-assistant-db -f

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Stop and remove all data (fresh start)
docker-compose down -v
```

---

## 💻 Local Development (Without Docker)

### Backend

```bash
cd apps/backend

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
copy .env.example .env

# Run migrations
alembic upgrade head

# Seed data
python -m app.seed

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/frontend/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### Ollama (Local LLM)

```bash
# Install Ollama: https://ollama.ai/download

# Pull model
ollama pull llama3.2

# Run (default port 11434)
ollama serve
```

---

## ⚙️ Environment Variables

Create `.env` file in `apps/backend/`:

```env
# App
APP_NAME=Schedule Assistant
DEBUG=true
SECRET_KEY=change-me-in-production

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/schedule_assistant

# CORS
CORS_ORIGINS=http://localhost:3000

# Defaults
DEFAULT_TIMEZONE=Asia/Bangkok
DEFAULT_WORKING_HOURS_START=09:00
DEFAULT_WORKING_HOURS_END=18:00

# LLM (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=60

# Gemini (optional)
AGENT_ENABLE_GEMINI=false
GEMINI_API_KEY=

# Prolog
PROLOG_MODE=subprocess
```

---

## 🔄 Database Migrations

```bash
cd apps/backend

# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View migration history
alembic history
```

---

## 🧪 Testing

```bash
cd apps/backend
pytest
```

---

## ⚠️ Troubleshooting

### Docker daemon not running
**Error**: `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`

**Solution**: Start Docker Desktop and wait until it's fully running.

---

### Port already in use
**Error**: `Bind for 0.0.0.0:5433 failed: port is already allocated`

**Solution**:
```bash
docker-compose down
docker-compose up -d postgres backend ollama
```

---

### Database tables don't exist
**Error**: `relation "users" does not exist`

**Solution**:
```bash
docker exec -it schedule-assistant-api alembic upgrade head
```

---

### LLM not responding
**Error**: `LLM connection failed` or slow responses

**Solution**:
```bash
# Check if Ollama is running
docker logs schedule-assistant-ollama

# Make sure model is pulled
docker exec -it schedule-assistant-ollama ollama pull llama3.2
```

---

### Reset everything (fresh start)
```bash
cd docker
docker-compose down -v
docker-compose up -d postgres backend ollama

# Wait 30 seconds, then:
docker exec -it schedule-assistant-api alembic upgrade head
docker exec -it schedule-assistant-api python -m app.seed
docker exec -it schedule-assistant-ollama ollama pull llama3.2
```

---

## 📝 Demo Credentials

After seeding, you'll have:
- **User ID**: `00000000-0000-0000-0000-000000000001`
- **Calendar ID**: `00000000-0000-0000-0000-000000000001`
- **Email**: `demo@example.com`

---

## 📄 License

MIT
