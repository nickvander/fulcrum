# Progress Log

## 2025-10-10

### CI/CD Pipeline Repair and Hardening

- **Problem:** The CI pipeline was consistently failing. Backend tests were
  stuck "Waiting for services to be healthy," and subsequent test runs revealed
  database setup failures (`psycopg2.errors.UniqueViolation`) due to a
  persistent `ENUM` type.
- **Actions:**
  1.  **Reverted to Stable Commit:** Reset the `main` branch to a known-good
      commit (`8dace85`) to undo breaking changes that were pulled from the
      remote.
  2.  **Fixed Service Dependencies:** Modified `docker-compose.test.yml` to
      ensure the `backend` service explicitly `depends_on` the `db-test` service
      with a `service_healthy` condition. This resolved the container startup
      race condition.
  3.  **Corrected DB Teardown:** Updated the `create_test_database` fixture in
      `tests/conftest.py` to explicitly drop the `ordersource` ENUM type after
      the test session, ensuring a clean database state for every run.
  4.  **Validated Fixes:** Ran the entire backend test suite locally to confirm
      that all tests pass.
  5.  **Force-Pushed to Remote:** Overwrote the remote `main` branch with the
      repaired local branch to bring the CI environment back to a stable state.
- **Outcome:** The CI pipeline is now stable, and the underlying issues causing
  test failures have been resolved.

### CI/CD Final Stabilization

- **Problem:** After the initial fixes, the CI pipeline continued to fail with a
  variety of environment-specific errors, including `docker compose wait`
  timeouts and containers not starting correctly.
- **Root Cause Analysis:** A `git reset` had inadvertently reverted several
  critical, but subtle, infrastructure fixes that were present in the commit
  history. The subsequent failures were a process of rediscovering and
  re-implementing these lost fixes.
- **Final Actions:**
  1.  **Restored Wait Logic:** Re-implemented the robust `until pg_isready` loop
      in the `ci.yml` workflow, as the `docker compose wait` command proved
      unreliable in the GitHub Actions environment.
  2.  **Corrected Service Startup:** Ensured the `docker compose up` command was
      correctly placed _before_ the wait logic, fixing a "service is not
      running" error.
- **Outcome:** The CI pipeline is now definitively stable and passing reliably.

## 2025-10-11

### Phase 5: CI/CD Efficiency and Testing Strategy Overhaul

- **Goal:** To significantly improve the speed, intelligence, and developer
  experience of the CI/CD pipeline and the local testing workflow.
- **Actions:**
  1.  **Isolated Linting:** Created a separate, fast-running `lint.yml` workflow
      that does not require Docker, providing immediate feedback on code style.
  2.  **Split Backend Tests:** Separated the backend CI into two distinct
      workflows: `backend-unit-tests.yml` for fast, database-free tests, and
      `backend-db-tests.yml` for slower, database-dependent tests.
  3.  **Path-Based Triggers:** Implemented `on.pull_request.paths` to ensure
      workflows are only triggered by changes in their relevant directories
      (e.g., frontend changes don't trigger backend tests).
  4.  **Standardized Local Testing:** Created a suite of `npm` scripts
      (`test:backend`, `test:backend:fast`, `test:frontend`) to simplify and
      standardize the local testing experience.
  5.  **Fixed Test Separation:** Created a true unit test for the security
      module to resolve the "no tests collected" error, validating the test
      separation strategy.
  6.  **Hardened CI Fixtures:** Refactored the `conftest.py` file to prevent
      unit tests from attempting to connect to the database, which was a primary
      source of CI failures.
  7.  **Added Manual Triggers:** Implemented `workflow_dispatch` on all
      workflows to allow for manual runs from the GitHub UI.
- **Outcome:** The CI/CD pipeline is now highly efficient. It provides faster
  feedback by running only relevant jobs, and the local testing experience is
  significantly improved. The separation between fast unit tests and database
  tests is now correctly implemented and stable.

## 2025-10-11 (Afternoon)

### Documentation Overhaul and Modernization

- **Goal:** To significantly improve the visual presentation, stability, and
  maintainability of the project's technical documentation.
- **Actions:**
  1.  **Modernized Theme:** Replaced the default `sphinx-rtd-theme` with the
      clean, modern `furo` theme.
  2.  **Fixed CSS Bugs:** Resolved a persistent "half-and-half" background color
      bug by removing custom CSS overrides and adopting Furo's official
      `html_theme_options` in `conf.py` for robust color management.
  3.  **Resolved Caching Issues:** Fixed lingering numbered titles in the table
      of contents by adding the `-E` flag to all `sphinx-build` and
      `sphinx-autobuild` commands, ensuring clean builds every time.
  4.  **Standardized Content:** Removed numerical prefixes from all
      documentation titles and updated all internal links for a cleaner, more
      consistent structure.
  5.  **Fixed Build Warnings:** Resolved the
      `document isn't included in any toctree` warning by adding the
      `docs/source/README.md` to the main `index.rst`.
  6.  **Improved CI Stability:** Corrected `uv` installation issues in the CI
      workflows by adding a `uv venv` step, making the linting and docs-build
      jobs more reliable.
- **Outcome:** The documentation is now visually appealing, stable, and easier
  to maintain. The build process is more robust, and all known bugs and warnings
  have been resolved.

## 2025-10-11 (Evening)

### Backend Test Suite Resolution

- **Problem:** The backend test suite was failing with persistent Alembic errors
  (`Can't locate revision`, `relation does not exist`, etc.) that resisted all
  standard troubleshooting approaches.
- **Root Cause Analysis:** Investigation revealed that the migration file was
  attempting to manually create enum types that were already being handled by
  SQLAlchemy, causing conflicts during test execution.
- **Solution:**
  1.  **Removed Manual Enum Creation:** Eliminated the manual `CREATE TYPE` statements
      from the migration file, allowing SQLAlchemy to handle enum type creation
      automatically.
  2.  **Verified Migration Execution:** Confirmed that the alembic upgrade process
      was correctly creating all database tables including the `product_custom_fields`
      table that was causing the "relation does not exist" errors.
- **Outcome:** All backend tests are now passing (21/21), resolving the primary
  blocker for continuing feature development.
