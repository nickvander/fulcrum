#!/bin/sh

# This script provides a reliable way to run Alembic migrations
# and then start the main application, ensuring the database is
# ready and up-to-date before the API becomes available.

set -e

# Activate the virtual environment
if [ -f "/app/venv/bin/activate" ]; then
    . /app/venv/bin/activate
else
    echo "Virtual environment not found. Skipping activation."
fi

# Wait for the database to be healthy
# The DATABASE_URL is expected to be in the format: postgresql://user:password@host:port/dbname
# We extract the host and port for pg_isready.
DB_HOST=$(echo $DATABASE_URL | cut -d '@' -f 2 | cut -d ':' -f 1)
DB_PORT=$(echo $DATABASE_URL | cut -d ':' -f 4 | cut -d '/' -f 1)
DB_USER=$(echo $DATABASE_URL | cut -d ':' -f 2 | cut -d '/' -f 3)

echo "Waiting for database at $DB_HOST:$DB_PORT..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done
>&2 echo "Postgres is up - executing command"

# Run database migrations
echo "Running database migrations..."
alembic -c /app/alembic.ini upgrade head

# Start the Uvicorn server
echo "Starting Uvicorn server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000