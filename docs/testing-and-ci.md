# 4. Testing Strategy & CI/CD

A robust testing strategy is crucial for maintaining code quality and stability.
This project uses a combination of automated unit tests, a linter, and a
Continuous Integration (CI) pipeline.

## Testing Framework

- **`pytest`:** A powerful and popular Python testing framework used to write
  and run our tests.
- **`httpx`:** Used via FastAPI's `TestClient` to make simulated HTTP requests
  to our API endpoints during tests.
- **In-Memory Database:** To ensure tests are fast and isolated, the test suite
  runs against an in-memory SQLite database, not the PostgreSQL database used
  for development. This is configured in `backend/tests/conftest.py`.

### Writing Tests

- All test files are located in the `backend/tests/` directory.
- Test files must be named `test_*.py`.
- Test functions must be named `test_*`.
- Tests use the `client` fixture (defined in `conftest.py`) to make API
  requests. This fixture ensures that each test runs within a clean, isolated
  database transaction.

### Running Tests Locally

To run the entire backend test suite, you must use the dedicated test database
configuration. Execute the following command from the project root:

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d --build && docker compose exec backend python -m pytest
```

This command starts the application using a separate PostgreSQL database
container (`db-test`) and then runs the `pytest` suite against it, ensuring
that your development data is not affected.

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

### Running Tests Locally

To run the entire frontend test suite, navigate to the `frontend/` directory and
run:

```bash
npm test
```

### Continuous Integration (CI) with GitHub Actions

The file `.github/workflows/ci.yml` defines a GitHub Actions workflow that
automates our quality checks for both the backend and frontend.

This workflow is triggered on every `push` and `pull_request` to the `main`
branch. It performs the following steps in parallel:

**Backend:**

1.  **Checkout Code:** Checks out the latest version of your repository.
2.  **Build Services:** Builds all the Docker containers using
    `docker compose up`.
3.  **Wait for Services:** Pauses to ensure the database and backend API are
    fully up and running before proceeding.
4.  **Run Database Migrations:** Executes `alembic upgrade head` to apply all
    database migrations. This ensures the test database has the correct schema
    before the tests run.
5.  **Run Linter:** Executes the `ruff check .` command. If the linter finds any
    errors, the workflow fails.
6.  **Run Tests:** Executes the `python -m pytest` command. If any test fails,
    the workflow fails.

**Frontend:**

1.  **Checkout Code:** Checks out the latest version of your repository.
2.  **Set up Node.js:** Installs the correct version of Node.js.
3.  **Install Dependencies:** Installs all the necessary npm packages.
4.  **Install Playwright Browsers:** Installs the browsers required by
    Playwright.
5.  **Run Tests:** Executes the `npm test` command. If any test fails, the
    workflow fails.

This ensures that code merged into the `main` branch always meets our quality
and correctness standards.
