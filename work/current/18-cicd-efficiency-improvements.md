# Task: Phase 5 - CI/CD Efficiency and Testing Strategy Overhaul

## 1. Goal

To significantly improve the speed and intelligence of the CI/CD pipeline and the local testing workflow. This will reduce feedback time for developers and ensure that only relevant tests are run based on code changes.

## 2. Problem Analysis

The current testing strategy has several inefficiencies:

1.  **Redundant Test Runs:** The CI pipeline runs the entire backend and frontend test suites on every commit to `main`, regardless of which part of the codebase was changed. A small frontend CSS change should not trigger the entire backend database test suite.
2.  **Slow Backend Tests:** The backend test suite is slow because it spins up Docker containers and a full PostgreSQL database for all tests, even for simple unit tests that don't require database access.
3.  **Lack of Granularity:** There is no distinction between fast unit tests and slower integration tests that require a database. This makes it difficult to get quick feedback on changes that don't impact the database schema or queries.
4.  **Outdated Documentation:** The `docs/testing-and-ci.md` file does not reflect the current state of the CI pipeline or the proposed improvements.

## 3. Proposed Solution

### Step 1: Implement Path-Based CI Triggers

-   **Action:** Modify the GitHub Actions workflows (`.github/workflows/backend-ci.yml` and `.github/workflows/frontend-ci.yml`) to run jobs conditionally based on file paths.
    -   The **backend** workflow will only trigger if changes are detected within the `backend/` directory.
    -   The **frontend** workflow will only trigger if changes are detected within the `frontend/` directory.
-   **Benefit:** This will eliminate redundant test runs and conserve CI resources.

### Step 2: Segregate Backend Tests

-   **Action:** Split the backend tests into two categories:
    1.  **Unit Tests:** Fast tests that do not require a database connection.
    2.  **Database Tests:** Slower integration tests that require a running PostgreSQL database.
-   **Implementation:**
    -   Use `pytest` markers to distinguish the tests. Any test function that requires the database (i.e., uses the `db` or `client` fixture) will be marked with `@pytest.mark.db`.
    -   Create a new, separate GitHub Actions workflow file (`.github/workflows/backend-unit-tests.yml`) that runs *only* the unit tests (`pytest -m "not db"`). This workflow will not use Docker Compose and will run very quickly.
    -   The existing `backend-ci.yml` will be renamed to `backend-db-tests.yml` and will be configured to run *only* the database tests (`pytest -m "db"`).
-   **Benefit:** Provides rapid feedback for most Python code changes, while still ensuring full database integrity for relevant changes.

### Step 3: Update Local Testing Scripts & Documentation

-   **Action:** Update the project's documentation and provide clear, simple commands for running the different test suites locally.
-   **Implementation:**
    -   Add new scripts to the root `package.json` file to simplify local test execution:
        -   `test:backend:unit`: Runs the fast backend unit tests.
        -   `test:backend:db`: Runs the slower backend database tests.
        -   `test:frontend`: Runs the frontend tests.
    -   Completely overhaul `docs/testing-and-ci.md` to reflect the new path-based CI triggers, the unit/database test split, and the new local testing commands.

### Step 4: Document Lessons Learned

-   **Action:** Add a "Troubleshooting" or "Known Issues" section to the updated testing documentation.
-   **Content:**
    -   Document the `psycopg2.errors.UniqueViolation` issue with PostgreSQL `ENUM` types and explain the solution (explicitly dropping the type in `conftest.py`). This will serve as a valuable reference for future development.
    -   Document the CI service startup issue caused by incorrect Docker Compose dependencies and the solution.

## 4. Validation

-   A push with only `frontend/` changes only triggers the frontend CI job.
-   A push with only non-database `backend/` changes triggers both the fast backend unit test job and the database test job.
-   The new `npm` scripts correctly execute the respective test suites locally.
-   The documentation is clear, accurate, and enables a new developer to easily run all test configurations.
