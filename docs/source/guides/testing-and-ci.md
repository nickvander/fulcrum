# Testing Strategy & CI/CD

A robust testing strategy is crucial for maintaining code quality and stability. This project uses a combination of automated tests, a linter, and a Continuous Integration (CI) pipeline to enforce these standards.

## Backend (Python)

### Testing Framework

- **`pytest`:** A powerful Python testing framework used to write and run our tests.
- **`httpx`:** Used via FastAPI's `TestClient` to make simulated HTTP requests to our API endpoints during tests.
- **PostgreSQL Test Database:** To ensure tests are both realistic and isolated, the database-dependent test suite runs against a dedicated PostgreSQL database managed by Docker, configured in `docker-compose.test.yml`.

### Running Tests Locally

A suite of `npm` scripts in the root `package.json` are available to standardize the testing process.

-   **Run the full backend test suite:**
    This is the most comprehensive backend test run. It uses Docker Compose to start the test database, run migrations, execute all backend tests (unit and database), and then shut down the containers.
    ```bash
    npm run test:backend
    ```

-   **Run only the fast backend unit tests:**
    This is ideal for quick checks when working on logic that does not directly touch the database. It runs `pytest` directly on your local machine.
    **Prerequisite:** This script requires a local Python environment with all dependencies from `backend/requirements.txt` installed. See the [Contributor Guide](./contributing.md) for setup instructions.
    ```bash
    npm run test:backend:fast
    ```

### Code Quality (Linting)

- **`ruff`:** An extremely fast Python linter that checks for a wide range of style and correctness issues. The linter is run as part of the CI pipeline.

## Frontend (Angular)

The frontend application uses the **[Web Test Runner](https://modern-web.dev/docs/test-runner/overview/)** with Playwright to execute its unit tests. The configuration can be found in `frontend/web-test-runner.config.mjs`.

-   **Run the frontend test suite:**
    ```bash
    npm run test:frontend
    ```

## Continuous Integration (CI) with GitHub Actions

To automate our quality checks, this project uses GitHub Actions. The workflows are defined in the `.github/workflows/` directory and are designed for efficiency by running jobs in parallel and triggering them only when relevant code changes. Workflows are triggered on every `push` and `pull_request` to the `main` branch.

### 1. Linting (`ci-lint.yml`)

- **Trigger:** Runs on changes to any file _except_ those in documentation-only directories.
- **Purpose:** Provides the fastest possible feedback on code style and basic errors using `ruff`.

### 2. Backend Unit Tests (`backend-02-unit-tests.yml`)

- **Trigger:** Runs only when files within the `backend/` directory are changed.
- **Purpose:** Provides rapid feedback on the backend logic without the overhead of database setup.
- **Process:** Runs the fast unit tests (`pytest -m "not db"`).

### 3. Backend Database Tests (`backend-01-db-tests.yml`)

- **Trigger:** Runs only when files within the `backend/` directory are changed.
- **Purpose:** Ensures the stability and correctness of the backend API and its database interactions.
- **Process:** Uses the `npm run test:backend` command to orchestrate the entire test run.

### 4. Frontend Testing (`frontend-tests.yml`)

- **Trigger:** Runs only when files within the `frontend/` directory are changed.
- **Purpose:** Ensures the stability and correctness of the frontend application.
- **Process:** Installs Node.js and npm dependencies, installs the Playwright browsers, and executes the `npm run test:frontend` command.