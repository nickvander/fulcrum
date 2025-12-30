# Scripts Directory

This directory contains utility scripts used by the project, including git hooks
for quality assurance.

## Git Hooks

These scripts are used as git hooks to enforce code quality:

### pre-commit-hook.sh

- Runs fast backend tests (excluding database tests)
- Runs the linter on the codebase
- Blocks commits if any checks fail

### pre-push-hook.sh

- Runs the full backend test suite (including database tests)
- Runs the frontend test suite
- Runs the linter on the codebase
- Blocks pushes if any checks fail

## Utility Scripts

### setup_mercadolibre_test.py

- **Description**: Automates the creation of MercadoLibre "Test Users" for both
  Global Selling (CBT) and Marketplace (Local) scenarios.
- **Dependencies**: Uses standard Python libraries (`urllib`, `json`). No
  external pip dependencies required.
- **Usage**:
  ```bash
  python setup_mercadolibre_test.py --token $ML_ACCESS_TOKEN --type local
  ```
- **Note**: Can be run using the system Python or inside the project's virtual
  environment.

### Running Live Integration Tests

We have a dedicated test suite for verifying the integration with MercadoLibre
using live API calls and generated test users.

1.  **Enter the Backend Container** (or ensure valid environment): These tests
    must run within the docker container to access the test database, or you
    must have a local DB setup.

2.  **Run with Token**: You must provide a valid `ML_ACCESS_TOKEN` (from a real
    MercadoLibre account) to allow the tests to generate test users.

    ```bash
    # Run via Docker Compose (Recommended)
    docker compose exec -e ML_ACCESS_TOKEN="APP_USR-..." backend pytest -m integration_ml tests/integration/test_mercadolibre_live.py
    ```

    **What this does:**
    - Creates a "Seller" and "Buyer" test user on MercadoLibre.
    - Publishes a `Product` from Fulcrum to MercadoLibre.
    - Verifies the item exists on ML.
    - (Optionally) Clean up is handled by ML's test user expiration policy.

These hooks ensure that code meets quality standards before being committed or
pushed to the repository.
