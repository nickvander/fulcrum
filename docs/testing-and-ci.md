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

To run the entire test suite, execute the following command from the project
root:

```bash
docker compose exec backend python -m pytest
```

## Code Quality (Linting)

- **`ruff`:** An extremely fast Python linter that checks for a wide range of
  style and correctness issues.
- Running the linter helps enforce a consistent code style and catches potential
  bugs before they are committed.

### Running the Linter Locally

To check the entire backend codebase for issues, run:

```bash
docker compose exec backend ruff check .
```

## Continuous Integration (CI) with GitHub Actions

The file `.github/workflows/ci.yml` defines a GitHub Actions workflow that
automates our quality checks.

This workflow is triggered on every `push` and `pull_request` to the `main`
branch. It performs the following steps:

1.  **Checkout Code:** Checks out the latest version of your repository.
2.  **Build Services:** Builds all the Docker containers using
    `docker compose up`.
3.  **Wait for Services:** Pauses to ensure the database and backend API are
    fully up and running before proceeding.
4.  **Run Linter:** Executes the `ruff check .` command. If the linter finds any
    errors, the workflow fails.
5.  **Run Tests:** Executes the `python -m pytest` command. If any test fails,
    the workflow fails.

This ensures that code merged into the `main` branch always meets our quality
and correctness standards.
