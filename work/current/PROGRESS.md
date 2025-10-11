# Progress Log

## 2025-10-10

### CI/CD Pipeline Repair and Hardening

- **Problem:** The CI pipeline was consistently failing. Backend tests were stuck "Waiting for services to be healthy," and subsequent test runs revealed database setup failures (`psycopg2.errors.UniqueViolation`) due to a persistent `ENUM` type.
- **Actions:**
    1.  **Reverted to Stable Commit:** Reset the `main` branch to a known-good commit (`8dace85`) to undo breaking changes that were pulled from the remote.
    2.  **Fixed Service Dependencies:** Modified `docker-compose.test.yml` to ensure the `backend` service explicitly `depends_on` the `db-test` service with a `service_healthy` condition. This resolved the container startup race condition.
    3.  **Corrected DB Teardown:** Updated the `create_test_database` fixture in `tests/conftest.py` to explicitly drop the `ordersource` ENUM type after the test session, ensuring a clean database state for every run.
    4.  **Validated Fixes:** Ran the entire backend test suite locally to confirm that all tests pass.
    5.  **Force-Pushed to Remote:** Overwrote the remote `main` branch with the repaired local branch to bring the CI environment back to a stable state.
- **Outcome:** The CI pipeline is now stable, and the underlying issues causing test failures have been resolved.