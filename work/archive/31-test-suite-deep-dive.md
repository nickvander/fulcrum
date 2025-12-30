# Task: Backend Test Suite Deep Dive & Final Bug Fixes

## Goal

To methodically diagnose and resolve the persistent backend test failures, and
then complete the final bug fixes and feature enhancements from the previous
session.

## Retrospective: The Alembic Problem

The backend test suite is consistently failing with Alembic-related errors
(`Can't locate revision`, `relation does not exist`, etc.). The following
strategies, despite being documented solutions, have failed:

1.  **Squashing Migrations:** Consolidating all migrations into a single file
    did not resolve the issue.
2.  **Destroying Docker Volumes:** Using `docker compose down -v` to ensure a
    clean database for every test run did not resolve the issue.
3.  **Alembic `stamp`:** Attempting to force the revision history with
    `alembic stamp head` did not work.
4.  **Modified Test Fixtures:** Both running migrations from within
    `conftest.py` and from the `npm` script have failed.

This indicates a deeper, more fundamental problem in the test environment's
interaction with Alembic.

## New Plan

### Phase 1: Isolate and Diagnose the Test Database

1.  **Isolate Alembic State:**
    - **Action:** Modify the `test:backend` script to run `alembic history` and
      `alembic current` immediately after the database container is up and
      migrations are run. This will show us what Alembic _believes_ the state of
      the database is.
2.  **Inspect Raw Database State:**
    - **Action:** Add a `psql` command to the `test:backend` script to directly
      query the `alembic_version` table in the test database. This will show us
      the _actual_ state of the database.
3.  **Nuke and Rebuild Migrations:**
    - **Hypothesis:** The squashed migration itself may be corrupt or
      referencing stale data.
    - **Action:** If the steps above don't reveal a simple fix, the plan is to:
      1.  Delete _all_ files in `backend/alembic/versions`.
      2.  Run
          `docker compose exec backend alembic revision --autogenerate -m "Initial baseline"`
          to create a single, clean, authoritative migration from the current
          state of the models.
      3.  Re-run the test suite against this single, clean migration.

### Phase 2: Complete Pending Features (After Tests are Green)

1.  **Fix Image Title/Description:**
    - **Action:** The backend models and schemas are complete, but the frontend
      implementation is not. I will complete the `updateImageDetails`
      functionality and ensure the data is saved correctly.
2.  **Fix Image Previews:**
    - **Action:** The logic for displaying staged image previews is partially
      implemented. I will complete this feature.
3.  **Verify Navigation on Save:**
    - **Action:** Once the API routing and data saving are confirmed to be
      working, I will verify that the frontend correctly navigates back to the
      product list after a successful save.

### Phase 3: Documentation

1.  **Action:** Add a new "Troubleshooting" section to the `GEMINI.md` file to
    document the learnings from the `sudo` and Alembic issues to prevent future
    developers from repeating these mistakes.
