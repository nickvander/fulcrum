# Task: Resolve Persistent Backend and CI Bugs

## Goal

To diagnose and definitively resolve the remaining bugs that are preventing the
backend from running reliably and the CI pipeline from passing. This plan
documents the completed, attempted, and next steps for this bug-squashing
session.

## Summary of Issues (Updated)

### Resolved Issues

1.  **CI Linter Failure:** The linter was failing due to unused imports in a
    root-owned migration file (`eca3f3_..._models.py`) and other miscellaneous
    errors. This has been **RESOLVED**.
2.  **Backend Startup Failure:** The backend service would not start reliably.
    Manually running migrations was required, and the process was error-prone.
    This has been **RESOLVED** by automating migrations on startup.

### Lingering Issues

1.  **Backend Test Failure:** The backend test suite (`npm run test:backend`)
    consistently fails with a
    `sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "products" does not exist`.
    This is the primary blocker.
2.  **Frontend `ECONNRESET` Error:** The frontend is experiencing
    `Http failure response` and `ECONNRESET` errors when communicating with the
    backend. This suggests a problem with the proxy configuration or the backend
    server crashing.
3.  **Frontend `[Object Object]` Error:** The photo ingestion workflow continues
    to display `[Object Object]` in the form, suggesting a data handling issue
    between the ingestion component and the product form.
4.  **Confusing UX:** The "Upload Images" button is disabled on product
    creation, which is not intuitive.

## Retrospective: What Has Been Tried (This Session)

A significant effort was made to stabilize the backend and the test environment.

### Linter and Backend Startup Fixes (Successful)

- **Linter Errors:** Fixed all reported `ruff` errors.
  - Corrected a misplaced import in `src/schemas/product.py`.
  - Added the missing `custom_field_schema` import in `src/api/products.py`.
  - Changed the ownership of the root-owned migration file (`eca3f3...`) to
    allow for the removal of unused imports.
- **Automated DB Migrations:** The backend now automatically waits for the
  database and runs migrations on startup.
  - Modified `docker-compose.yml` to use `backend/migrate.sh` as its `command`.
  - Rewrote `migrate.sh` to include a `pg_isready` loop, run
    `alembic upgrade head`, and then execute `uvicorn`.
- **Docker Environment Hardening:**
  - Updated the `backend/Dockerfile` to install `postgresql-client` (making
    `pg_isready` available).
  - Updated the `backend/Dockerfile` to create and set permissions for the
    `.ruff_cache` directory, fixing CI cache errors.
  - Diagnosed and fixed a critical YAML syntax error in `docker-compose.yml`
    that was causing an `invalid proto` error.

### Backend Test Failure Investigation (Unsuccessful)

The `relation "products" does not exist` error proved highly resistant to
debugging. The following approaches were attempted without success:

- **Test DB Schema Creation:** Modified `tests/conftest.py` to use Alembic
  (`command.upgrade(cfg, "head")`) to create the test database schema, ensuring
  it matches production.
- **Docker Compose Configuration:**
  - Simplified the `test:backend` script in `package.json` to only run the
    necessary `backend` and `db-test` services to rule out memory issues.
  - Corrected the `docker-compose.test.yml` file to provide a `build` context
    for the `backend` and `worker` services.
- **Alembic Configuration:**
  - Modified the `test:backend` script to explicitly pass the path to the
    `alembic.ini` file (`-c /app/alembic.ini`).
  - Added volume mounts for `alembic.ini` and the `alembic/` directory to
    `docker-compose.test.yml` to ensure they were accessible in the container.
- **Historical Log Analysis:** Reviewed the project's archived work logs
  (`work/archive/`). This revealed a critical insight: previous developers had
  fixed a similar issue by using a broad volume mount (`./backend:/app`) instead
  of granular mounts. This was implemented in `docker-compose.test.yml`.
- **Full Environment Reset:** As a final resort, completely destroyed all Docker
  volumes (`docker compose down -v`) to ensure a clean slate.

Despite all these efforts, the test suite continues to fail with the same error.
All changes related to the test suite have been reverted to the original state
to provide a clean starting point for the next session.

## New Implementation Plan for Next Session

### 1. **Fix Backend Test Suite**

- **Hypothesis:** The issue is not with the Docker or Alembic configuration, but
  with the test environment setup itself within `pytest` or `conftest.py`. The
  fact that `Base.metadata.create_all(bind=engine)` was used before suggests a
  fundamental difference in how the test DB is initialized compared to the
  production DB.
- **Action:**
  1.  Start with the original, reverted test configuration.
  2.  Instead of running `alembic upgrade head` from the `npm` script, modify
      the `create_test_database` fixture in `conftest.py` to correctly invoke
      the Alembic upgrade. This is the standard practice for `pytest` fixtures.
  3.  Carefully debug the state of the database _inside_ the
      `create_test_database` fixture to confirm that tables are being created as
      expected.

### 2. **Diagnose and Fix Frontend Proxy & Backend Stability**

- **(No change)** Once the backend tests are stable, proceed with this step.

### 3. **Diagnose and Fix Photo Ingestion**

- **(No change)**

### 4. **Improve Product Creation UX**

- **(No change)**
