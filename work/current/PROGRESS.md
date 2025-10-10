# Project Progress Log

This file tracks the progress of the current development phase. For a history of
completed phases, see the files in the `work/archive/` directory.

## Phase 3: Intelligent Product Ingestion & Indexing

- **October 8, 2025:** Completed the initial implementation for "Phase 3 -
  Intelligent Product Ingestion & Indexing".
  - **Backend:** Established endpoints for file uploads and AI analysis.
  - **Frontend:** Created the `HardwareService` and `ProductIngestionComponent`
    with barcode scanning and photo capture capabilities.
  - **Troubleshooting:** Resolved numerous critical startup and build issues
    across the backend and frontend, resulting in a stable, runnable
    application. All CI tests are now passing.

## Phase 3.5: Hardening & Feature Completion

- **October 8, 2025:** Planned the "Hardening & Feature Completion" phase.

  - Created a new work plan to address all outstanding `TODO` comments and

    fully implement the core product CRUD and intelligent ingestion workflows

    before beginning Phase 4.

  - **Troubleshooting & Key Learnings:**

    - **Backend Startup:** A persistent "Connection reset by peer" error was

      traced to a series of cascading startup failures. The key lessons were:

      1.  **Docker Volumes:** Granular volume mounts (`./backend/src:/app/src`)

          prevented root-level config files (`alembic.ini`) from being included

          in the container. This was fixed by mounting the entire directory

          (`./backend:/app`) and using an anonymous volume (`/app/venv`) to

          protect the installed dependencies.

      2.  **Pydantic Configuration:** Environment variables set in

          `docker-compose.yml` for one service (e.g., `db`) can leak into

          others and take precedence over `.env` files. The `Settings` model

          was made more robust to handle this and construct the `DATABASE_URL`

          dynamically.

      3.  **Docker Caching:** A missing dependency (`python-multipart`) was not

          being installed even after being added to `requirements.txt` due to

          aggressive Docker layer caching. This required a temporary workaround

          (disabling the endpoint) and highlights the need for `--no-cache`

          builds when debugging dependency issues.

    - **Frontend CI Tests:** The `HardwareService` test repeatedly failed in the

      CI environment with a "Permission denied" error.

      1.  **Read-Only Globals:** The headless browser in the CI pipeline enforces

          a read-only `navigator.mediaDevices` object as a security feature.

      2.  **Robust Mocking:** Standard `spyOn` and object replacement failed. The

          definitive solution was to use `Object.defineProperty` to temporarily

          make the property writable for the duration of the test, which is the

          correct pattern for mocking locked-down global objects.

- **October 9, 2025:** Completed the "Hardening & Feature Completion" phase.
  - **Features:** Implemented all planned features, including the full product
    CRUD lifecycle, reactive state management, global user feedback (loading
    and notifications), photo ingestion, and product image uploads.
  - **Testing:** Wrote a comprehensive suite of unit tests for all new and
    modified frontend components and services.
  - **Troubleshooting:** Resolved a series of persistent and complex CI test
    failures related to Angular Material's `MatDialog` service in a
    standalone component testing environment. The key learning was that for
    standalone components with their own complex module imports (like
    `SharedModule`), the most robust testing strategy is to use
    `TestBed.overrideComponent` to remove the problematic module and stub out
    child components. This completely isolates the component under test and
    avoids dependency conflicts. All backend and frontend tests are now
    passing in the CI pipeline.
- **October 9, 2025:** Planned the "Polishing & Refinements" phase.
  - Created a new work plan (`14-polishing-and-refinements.md`) to address
    outstanding UI/UX improvements before beginning Phase 4.

## Phase 3.6: Polishing & Refinements

- **October 10, 2025:** Completed the "Polishing & Refinements" phase.
  - **Features:** Implemented all planned UI/UX improvements, including
    reactive search and enhanced image management (delete and set primary).
  - **Testing:** All backend and frontend tests are passing, ensuring the
    stability of the new features.

## Phase 3.7: Admin Features & UX Enhancements

- **October 10, 2025:** Completed the "Admin Features & UX Enhancements" phase.
  - **Backend:** Implemented a secure foundation for administration by adding an
    `is_superuser` flag to the `User` model, creating a database migration,
    and building a full suite of protected API endpoints for user management
    (CRUD operations).
  - **Frontend:** Developed a complete, lazy-loaded `UsersModule` for admins to
    manage users. Enhanced the `ProductListComponent` with instant client-side
    filtering and a user-friendly "empty state" to improve usability. Added a
    "Users" link to the main navigation, visible only to superusers.

## Testing Infrastructure

- **October 10, 2025:** Investigated and resolved critical test failures.
  - **Frontend:** All frontend tests are now passing. The test failures were
    caused by a combination of incorrect file naming conventions and issues
    with how Angular's `TestBed` handles standalone components. The solution
    involved renaming service files, converting several components to
    `standalone: true`, and updating the `TestBed` configuration in all
    relevant spec files to correctly import components and provide necessary
    dependencies.
  - **Backend:** The backend test runner is consistently failing with a
    `ModuleNotFoundError: No module named 'jose'`. This issue persists even
    after adding the dependency, rebuilding the Docker container with
    `--no-cache`, and trying multiple execution strategies. This is a critical
    blocker.
  - **Next Step:** The immediate priority for the next session is to create a
    dedicated plan to diagnose and fix the backend testing environment before
    proceeding with the "Admin Module Hardening & Feature Completion" phase.

- **October 10, 2025:** Resolved backend testing environment.
  - **Troubleshooting:** The persistent `ModuleNotFoundError` was traced to the
    broad `./backend:/app` volume mount in `docker-compose.yml`, which was
    corrupting the container's virtual environment. The issue was resolved by
    switching to more granular volume mounts, which isolate the container's
    `venv` from the host filesystem. Subsequent `AttributeError` issues were
    resolved by correcting package `__init__.py` files to ensure proper module
    and instance imports.
  - **Testing:** All backend tests are now passing. The CI pipeline is unblocked.
  - **Next Step:** Proceed with the "Admin Module Hardening & Feature
    Completion" phase.