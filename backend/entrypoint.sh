#!/usr/bin/env sh
# Backend container entrypoint.
#
# Why this exists: the lifespan hook in `src.main` tries to create
# the FIRST_SUPERUSER on startup, but if it runs before alembic has
# applied migrations, the `users` table doesn't exist yet and the
# bootstrap silently fails (an operator then has to `docker restart`
# the backend manually). This wrapper runs migrations FIRST so the
# lifespan hook always sees a fully-migrated schema, then execs the
# command passed by docker-compose (defaults to uvicorn).

set -e

# Wait for the database to accept connections. Postgres can be
# "started" but not yet ready, so we retry with a short backoff.
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-fulcrum}"

echo "[entrypoint] waiting for postgres at $DB_HOST:$DB_PORT..."
for i in $(seq 1 30); do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; then
        echo "[entrypoint] postgres is ready"
        break
    fi
    sleep 1
done

# Run migrations. `--with-lock` is the default in alembic; we don't
# need anything fancier because docker-compose serializes container
# startup via `depends_on: condition: service_healthy`.
echo "[entrypoint] running alembic migrations..."
alembic upgrade head

# Then hand off to whatever command the image / compose passed.
echo "[entrypoint] starting: $@"
exec "$@"
