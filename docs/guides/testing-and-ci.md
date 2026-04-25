# Testing Strategy & CI/CD

A robust testing strategy is crucial for maintaining code quality and stability.
This project uses a combination of automated tests, a linter, and a Continuous
Integration (CI) pipeline to enforce these standards.

## Backend (Python)

### Testing Framework

- **`pytest`:** A powerful Python testing framework used to write and run our
  tests.
- **`httpx`:** Used via FastAPI's `TestClient` to make simulated HTTP requests
  to our API endpoints during tests.
- **PostgreSQL Test Database:** To ensure tests are both realistic and isolated,
  the database-dependent test suite runs against a dedicated PostgreSQL database
  managed by Docker, configured in `docker-compose.test.yml`.

### Running Tests Locally

A suite of `npm` scripts in the root `package.json` are available to standardize
the testing process.

- **Run the full backend test suite:** This is the most comprehensive backend
  test run. It uses Docker Compose to start the test database, run migrations,
  execute all backend tests (unit and database), and then shut down the
  containers.

  ```bash
  npm run test:backend
  ```

- **Run only the fast backend unit tests:** This is ideal for quick checks when
  working on logic that does not directly touch the database. It runs `pytest`
  directly on your local machine. **Prerequisite:** This script requires a local
  Python environment with all dependencies from `backend/requirements.txt`
  installed. See the [Contributor Guide](./contributing.md) for setup
  instructions.
  ```bash
  npm run test:backend:fast
  ```

### Code Quality (Linting)

- **`ruff`:** An extremely fast Python linter that checks for a wide range of
  style and correctness issues. The linter is run as part of the CI pipeline.

## Frontend (Angular)

The frontend application uses **[Vitest](https://vitest.dev/)** (via Angular v21
stable support) to execute its unit tests. The configuration is managed by the
Angular CLI and `vitest.config.ts`.

- **Run the frontend test suite:**
  ```bash
  npm run test:frontend
  ```

### Frontend Testing Best Practices

To ensure test stability and prevent hangs (especially in CI environments),
follow these guidelines:

1.  **Manage Subscriptions:** Always unsubscribe from Observables. Use the
    `takeUntil(this.destroy$)` pattern in components and ensure `ngOnDestroy` is
    called. In tests, avoid leaving open subscriptions.
2.  **Mock Services:** Mock all dependent services using `jasmine.createSpyObj`.
    Avoid using real services that make HTTP calls or have complex
    initialization logic.
3.  **Mock Initialization Logic:** For components that initialize data in
    `ngOnInit` (like `ProductForm`), mock the initialization service (e.g.,
    `ProductFormInitializerService`) to return controlled test data immediately.
4.  **Avoid `fixture.whenStable()`:** In some test environments,
    `await fixture.whenStable()` can hang indefinitely if there are pending
    macro-tasks (like `setInterval` or open subscriptions). Use `fakeAsync` and
    `tick()` if you need to control time, or rely on `fixture.detectChanges()`
    for synchronous updates.
5.  **Isolate Tests:** If a test suite hangs, use `fit` to isolate specific
    tests and identify the culprit. Stub out child components using
    `TestBed.overrideComponent` to isolate the component under test.
6.  **Standalone Components:** When testing standalone components that import
    complex child components, use `TestBed.overrideComponent` to remove those
    imports and add `NO_ERRORS_SCHEMA`. This prevents child component
    initialization from interfering with the unit test.

## End-to-End (E2E) Testing

The project uses **[Playwright](https://playwright.dev/)** for End-to-End
testing. These tests simulate real user interactions across the full stack
(Frontend + Backend + Database).

- **Configuration:** `playwright.config.ts`
- **Test Directory:** `e2e/`

### Running E2E Tests Locally

To run E2E tests, you must have the backend and frontend running.

1.  **Start the Backend:**
    ```bash
    docker compose up -d
    ```
2.  **Start the Frontend:**
    ```bash
    npm start --prefix frontend
    ```
3.  **Run Tests:**
    ```bash
    npm run test:e2e
    ```

## Continuous Integration (CI) with GitHub Actions

To automate our quality checks, this project uses GitHub Actions. The workflows
are defined in the `.github/workflows/` directory and are designed for
efficiency by running jobs in parallel and triggering them only when relevant
code changes. Workflows are triggered on every `push` and `pull_request` to the
`main` branch.

### Local Quality Assurance with Git Hooks

In addition to the CI pipeline, this project uses git hooks to enforce code
quality before commits and pushes:

- **pre-commit hook:** Runs fast backend tests, linter, and i18n validation to
  catch issues early in the development process.
- **pre-push hook:** Runs the full CI test suite (backend, frontend, linting,
  and i18n validation) to ensure all code passes comprehensive tests before
  being pushed to the repository.

### 1. Linting (`ci-lint.yml`)

- **Trigger:** Runs on changes to any file _except_ those in documentation-only
  directories.
- **Purpose:** Provides the fastest possible feedback on code style and basic
  errors using `ruff`.

### 2. Backend Unit Tests (`backend-02-unit-tests.yml`)

- **Trigger:** Runs only when files within the `backend/` directory are changed.
- **Purpose:** Provides rapid feedback on the backend logic without the overhead
  of database setup.
- **Process:** Runs the fast unit tests (`pytest -m "not db"`).

### 3. Backend Database Tests (`backend-01-db-tests.yml`)

- **Trigger:** Runs only when files within the `backend/` directory are changed.
- **Purpose:** Ensures the stability and correctness of the backend API and its
  database interactions.
- **Process:** Uses the `npm run test:backend` command to orchestrate the entire
  test run.

### 4. Frontend Testing (`frontend-tests.yml`)

- **Trigger:** Runs only when files within the `frontend/` directory are
  changed.
- **Purpose:** Ensures the stability and correctness of the frontend
  application.
- **Process:** Installs Node.js and npm dependencies, installs the Playwright
  browsers, and executes the `npm run test:frontend` command.

### 5. E2E Tests (`e2e-tests.yml`)

- **Trigger:** Runs on `push` and `pull_request` to the `main` branch.
- **Purpose:** Validates critical user flows across the full stack.
- **Process:**
  - Sets up Node.js and Python.
  - Starts the full backend stack (DB, Redis, API) using Docker Compose.
  - Starts the frontend application.
  - Executes Playwright tests (`npm run test:e2e`).
  - Uploads test reports as artifacts.

### 6. Live Integration Tests (MercadoLibre)

- **Purpose:** Verifies the full sync lifecycle with MercadoLibre using live API
  calls and generated test users.
- **Location:** `backend/tests/integration/test_mercadolibre_live.py`
- **Prerequisites:** Requires a valid `ML_ACCESS_TOKEN` from a real developer
  account.
- **Running Locally:**
  ```bash
  docker compose exec -e ML_ACCESS_TOKEN="YOUR_TOKEN" backend pytest -m integration_ml tests/integration/test_mercadolibre_live.py
  ```
