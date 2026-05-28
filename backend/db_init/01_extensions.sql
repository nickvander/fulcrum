-- Auto-installed on a fresh postgres data dir via the
-- pgvector/pgvector image's /docker-entrypoint-initdb.d hook.
-- Without this, the first `alembic upgrade head` fails with
-- `type "vector" does not exist` because the very first migration
-- creates a `VECTOR(384)` column on `products.embedding`.

CREATE EXTENSION IF NOT EXISTS vector;
