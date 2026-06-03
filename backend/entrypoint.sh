#!/bin/sh
# entrypoint.sh
# ───────────────
# Runs migrations and boots the FastAPI server inside the container.

set -e

# Extract host and port from DATABASE_URL for netcat readiness check
# Standard DATABASE_URL: postgresql+asyncpg://user:pass@host:port/dbname
# We extract the host and port using simple parsing
DB_HOST=$(echo "$DATABASE_URL" | sed -E 's/.*@([^:]+).*/\1/')
DB_PORT=$(echo "$DATABASE_URL" | sed -E 's/.*:([0-9]+)\/.*/\1/')

# If parsing fails, default to 5432
if [ -z "$DB_PORT" ] || echo "$DB_PORT" | grep -q "[^0-9]"; then
  DB_PORT=5432
fi

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
until nc -z -v -w3 "$DB_HOST" "$DB_PORT"; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done
echo "PostgreSQL is up and running!"

# Run Alembic migrations to align database schema
echo "Running database migrations..."
alembic upgrade head
echo "Database migrations completed successfully!"

# Start FastAPI application using Uvicorn
# --workers 4: standard worker count for containerized environment
# --proxy-headers: tells uvicorn to trust X-Forwarded-For headers from Nginx/ALB
echo "Starting Uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --workers 4
