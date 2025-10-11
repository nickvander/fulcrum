# Task: Phase 5 - CI/CD Efficiency and Testing Strategy Overhaul

## 1. Goal

To significantly improve the speed, intelligence, and developer experience of the
CI/CD pipeline and the local testing workflow. This will reduce feedback time,
conserve resources, and ensure a stable and predictable testing environment.

## 2. Refined Implementation Strategy

To avoid breaking the build, these changes will be implemented incrementally
across three stages. Documentation will be updated *as each stage is completed*
to ensure it remains accurate throughout the process.

---

### **Stage 1: Foundational CI Improvements (Low-Risk First Steps)**

The first priority is to get immediate efficiency gains without touching the
test-running logic itself.

1.  **Isolate Linting:**
    -   **Action:** Create a new, separate GitHub Actions workflow for `ruff`.
        This job will be extremely fast as it doesn't need to build Docker
        containers or install dependencies beyond the linter itself.
    -   **Benefit:** Provides the fastest possible feedback on code style and
        basic errors on every push.

2.  **Implement Path-Based CI Triggers:**
    -   **Action:** Modify the existing `backend-ci.yml` and `frontend-ci.yml`
        workflows to use `on.pull_request.paths` and `on.push.paths`. The
        backend job will only run on changes to the `backend/` directory, and
        the frontend job only on changes to `frontend/`.
    -   **Benefit:** Immediately stops running irrelevant test suites, saving
        significant time and CI resources.

3.  **Update Documentation (Stage 1):**
    -   **Action:** After implementing the above, update the CI section of
        `docs/testing-and-ci.md` to describe the new, parallel linting job and
        the path-based triggers.

---

### **Stage 2: Overhauling the Backend Test Suite**

This is the core of the overhaul. All steps will be performed and validated
locally first before any CI workflows are modified.

1.  **Mark the Tests:**
    -   **Action:** Manually inspect every test in the `backend/tests/`
        directory. Any test that uses the `db` or `client` fixture will be
        marked with `@pytest.mark.db`.
    -   **Benefit:** Creates a clear, explicit separation between fast unit
        tests and slower database-dependent tests.

2.  **Create Smart Local Scripts via NPM:**
    -   **Action:** Add a suite of scripts to the root `package.json` to
        standardize local testing.
        -   `npm run test:backend:unit`: Runs only the fast unit tests (`pytest -m "not db"`).
        -   `npm run test:backend:db`: A "one-touch" script that starts the
            test containers, runs the database tests (`pytest -m "db"`), and
            then shuts them down.
        -   `npm run test:frontend`: Remains as is (`npm test --prefix frontend`).
        -   `npm run test:all`: Runs all three of the above scripts.
    -   **Benefit:** Dramatically improves the developer experience with simple,
        intuitive commands.

3.  **Split CI Workflows for Backend:**
    -   **Action:** Once the scripts are validated locally, modify the GitHub
        Actions to use them.
        -   Rename `backend-ci.yml` to `backend-db-tests.yml` and configure it
            to run `npm run test:backend:db`.
        -   Create a new, parallel `backend-unit-tests.yml` workflow that runs
            `npm run test:backend:unit` without Docker.
    -   **Benefit:** Provides rapid feedback for most backend changes.

4.  **Update Documentation (Stage 2):**
    -   **Action:** Overhaul the "Running Tests Locally" section of
        `docs/testing-and-ci.md` to remove the old `docker compose` commands
        and replace them with instructions for the new, simplified `npm`
        scripts.

---

### **Stage 3: Finalization and Cleanup**

1.  **Document Lessons Learned:**
    -   **Action:** Add a "Troubleshooting" section to the testing
        documentation.
    -   **Content:** Detail the `psycopg2.errors.UniqueViolation` with ENUMs
        and the Docker volume corruption issue to preserve this knowledge.
    -   **Benefit:** Prevents future developers from re-diagnosing the same
        problems.

2.  **Format and Validate:**
    -   **Action:** Run `npm run format:md` to automatically format all
        modified Markdown files (`GEMINI.md`, `docs/testing-and-ci.md`, and
        this plan) to ensure they adhere to the project's 80-character line
        width standard.
    -   **Benefit:** Maintains a clean and consistent documentation style.

## 3. Future Considerations

-   **Frontend Test Segregation:** Consider a similar "unit" vs. "e2e" split
    for frontend tests in the future if the suite becomes slow.
-   **Automatic Test Marking:** Explore `pytest` hooks to automatically apply
    the `db` marker to any test using the `db` fixture for improved robustness.
