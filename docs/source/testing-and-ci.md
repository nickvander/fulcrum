# Testing Strategy & CI/CD

A robust testing strategy is crucial for maintaining code quality and stability.
This project uses a combination of automated unit tests, a linter, and a
Continuous Integration (CI) pipeline.

## Testing Framework

- **`pytest`:** A powerful and popular Python testing framework used to write
  and run our tests.
- **`httpx`:** Used via FastAPI's `TestClient` to make simulated HTTP requests
  to our API endpoints during tests.
- **PostgreSQL Test Database:** To ensure tests are both realistic and isolated,
  the test suite runs against a dedicated PostgreSQL database managed by Docker.
  This is configured in `docker-compose.test.yml`.

### Writing Tests

- All test files are located in the `backend/tests/` directory.
- Test files must be named `test_*.py`.
- Test functions must be named `test_*`.
- Tests that interact with the database use the `client` or `db` fixtures
  (defined in `conftest.py`) and are marked with `@pytest.mark.db`.

### Running Tests Locally

A suite of `npm` scripts are available to standardize the testing process.

-   **Run all tests (frontend and backend):**
    This is the most comprehensive test run.
    ```bash
    npm run test:all
    ```

-   **Run only the frontend tests:**
    ```bash
    npm run test:frontend
    ```

-   **Run the full backend test suite:**
    This command will automatically start the test database, run migrations,
    execute all backend tests (unit and database), and then shut down the
    containers.
    ```bash
    npm run test:backend
    ```

-   **Run only the fast backend unit tests:**
    This is ideal for quick checks when working on logic that does not directly
    touch the database.

    **Prerequisite:** This script requires a local Python 3 environment with all
    dependencies from `backend/requirements.txt` installed.
    ```bash
    npm run test:backend:fast
    ```

## Code Quality (Linting)

- **`ruff`:** An extremely fast Python linter that checks for a wide range of
  style and correctness issues.
- Running the linter helps enforce a consistent code style and catches potential
  bugs before they are committed.

## Frontend (Angular)

The frontend application uses the
[Web Test Runner](https://modern-web.dev/docs/test-runner/overview/) with
Playwright to execute its unit tests. All components and services generated via
the Angular CLI include a corresponding `.spec.ts` file.

The test environment is configured to use a headless Chromium browser, making it
suitable for both local development and automated execution in a CI/CD pipeline.

### Continuous Integration (CI) with GitHub Actions

To automate our quality checks, this project uses GitHub Actions. The workflows
are defined in the `.github/workflows/` directory and are designed for
efficiency by running jobs in parallel and triggering them only when relevant
code changes.

Workflows are triggered on every `push` and `pull_request` to the `main` branch.

#### 1. Linting (`lint.yml`)

- **Trigger:** Runs on changes to any file _except_ those in documentation-only
  directories (e.g., `/docs`).
- **Purpose:** Provides the fastest possible feedback on code style and basic
  errors.
- **Process:** This job checks out the code, installs `ruff`, and runs the
  linter. It does not require Docker or any other heavy dependencies, so it
  completes very quickly.

#### 2. Backend Unit Tests (`backend-unit-tests.yml`)

- **Trigger:** Runs only when files within the `backend/` directory are changed.
- **Purpose:** Provides rapid feedback on the backend logic without the overhead
  of database setup.
- **Process:** This job checks out the code, installs Python dependencies, and
  runs the fast unit tests (`pytest -m "not db"`).

#### 3. Backend Database Tests (`backend-db-tests.yml`)

- **Trigger:** Runs only when files within the `backend/` directory are changed.
- **Purpose:** Ensures the stability and correctness of the backend API and its
  database interactions.
- **Process:** This workflow uses the `npm run test:backend:db` command to
  orchestrate the entire test run, including building and starting Docker
  containers, running database migrations, and executing the tests.

#### 4. Frontend Testing (`frontend-ci.yml`)

- **Trigger:** Runs only when files within the `frontend/` directory are
  changed.
- **Purpose:** Ensures the stability and correctness of the frontend
  application.
- **Process:**
  1.  **Checkout Code:** Checks out the latest version of your repository.
  2.  **Set up Node.js:** Installs the correct version of Node.js.
  3.  **Install Dependencies:** Installs all the necessary npm packages.
  4.  **Install Playwright Browsers:** Installs the browsers required by
      Playwright.
  5.  **Run Tests:** Executes the `npm test` command. If any test fails, the
      workflow fails.

This setup ensures that code merged into the `main` branch always meets our
quality and correctness standards while minimizing unnecessary CI runs.

## Troubleshooting

### `psycopg2.errors.UniqueViolation` with ENUMs

- **Symptom:** `pytest` fails with a `UniqueViolation` related to a PostgreSQL
  `ENUM` type, even though the database is supposed to be clean.
- **Cause:** This can happen if a previous test run failed and didn't clean up
  properly. Alembic may not correctly handle `ENUM` types that already exist in
  the database, leading to this error on subsequent runs.
- **Solution:** The most reliable solution is to completely reset the test
  database volume. The `npm run test:backend:db` script handles this
  automatically by design, but if you are running `docker compose` manually, you
  can run `docker compose -f docker-compose.test.yml down -v` to remove the
  volume.

### Docker Volume Corruption on Windows/WSL

- **Symptom:** Docker fails to start, complaining about corrupted data volumes,
  often after a system crash or unexpected shutdown.
- **Cause:** The Docker Desktop data volume can become corrupted.
- **Solution:** In Docker Desktop, go to `Settings > Resources > Advanced` and
  click the "Reset disk" button. This will destroy all existing containers and
  volumes but will resolve the corruption issue.
