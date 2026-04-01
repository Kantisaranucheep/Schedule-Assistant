#!/bin/bash
# schedule-assistant/apps/backend/entrypoint.sh
# Entrypoint script for backend container - runs migrations before starting the app

set -e

echo "========================================="
echo "Schedule Assistant Backend - Starting..."
echo "========================================="

# Wait for database to be ready
echo "Waiting for PostgreSQL to be ready..."

# Use environment variables from docker-compose
DB_HOST=${POSTGRES_HOST:-postgres}
DB_PORT=${POSTGRES_PORT:-5432}
DB_USER=${POSTGRES_USER:-postgres}
DB_NAME=${POSTGRES_DB:-schedule_assistant}

# Wait for PostgreSQL
for i in {1..30}; do
    if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    echo "⏳ Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# Final check
if ! PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
    echo "❌ PostgreSQL failed to start after 60 seconds"
    exit 1
fi

# Run database migrations
echo "========================================="
echo "Running database migrations..."
echo "========================================="
cd /app

if alembic upgrade head; then
    echo "✅ Migrations completed successfully!"
else
    echo "❌ Migration failed!"
    exit 1
fi

# Start the application
echo "========================================="
echo "Starting FastAPI application..."
echo "========================================="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

