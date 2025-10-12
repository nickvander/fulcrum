# Project: Fulcrum

## Goal

To build a comprehensive, AI-first platform to streamline the entire product
lifecycle, including inventory management, supplier orders, multi-channel sales,
and business analytics. The core management interface will be a Progressive Web
App (PWA) for a seamless experience on web, Android, and iOS from a single
codebase.

## Tech Stack

- **Frontend (Management PWA & E-commerce):** Angular, Angular Material, Angular
  PWA module (`@angular/pwa`).
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic, Pydantic, Celery & Redis.
- **Database:** PostgreSQL with the `pgvector` extension.
- **Deployment:** Docker & Docker Compose for the backend, static hosting for
  the e-commerce frontend.

## Development Principles

To ensure a maintainable and scalable codebase, this project adheres to the
following principles:

1.  **Repository Pattern (Backend):** All database interactions are abstracted
    away from the API layer using repositories.
    - A generic `CRDBase` class provides common CRUD operations.
    - Model-specific repositories (e.g., `crud_product.py`) inherit from
      `CRUDBase` and implement any additional, model-specific logic.
    - API endpoints should be thin and delegate all database logic to the
      repository layer.

2.  **Centralized API Routing (Backend):** The API routing for each version is
    centralized in a single file (e.g., `src/api/v1/api.py`).
    - This file is responsible for including all endpoint routers and defining
      their prefixes and tags.
    - The main `main.py` application file should only include the top-level API
      router for each version.

3.  **Security Best Practices (Backend):**
    - Passwords are never stored in plaintext. They are hashed using `bcrypt`
      via the `passlib` library.
    - Authentication and authorization mechanisms will be implemented to protect
      sensitive endpoints.

4.  **Efficient Testing (Backend):**
    - Database fixtures are session-scoped to improve test performance.
    - Reusable data fixtures are used to keep tests clean and DRY.

5.  **Frontend Testing:** The frontend application uses the Web Test Runner with
    Playwright for unit testing. All new components and services must be
    accompanied by a corresponding `.spec.ts` file with adequate test coverage.

6.  **Centralized & Thematic Documentation:** All technical documentation is
    maintained within the `/docs` directory and built with Sphinx. It follows a
    thematic structure to ensure information is easy to find:
    - `/docs/source/getting-started`: For essential setup guides.
    - `/docs/source/guides`: For practical, step-by-step "how-to" documents.
    - `/docs/source/explanation`: For deep dives into architecture and concepts.
    - `/docs/source/reference`: For technical references like API specs or
      config. This centralized hub is the single source of truth for the
      project.

7.  **Markdown Formatting:** All Markdown files (`.md`) in this project are
    formatted using Prettier.
    - **Recommended:** Use a Prettier extension in your code editor (e.g., for
      VS Code) to format files automatically on save.
    - **Alternative:** To format all Markdown files from the command line, run
      `npm run format:md` from the root of the project.

8.  **Documentation Review:** At the end of each development phase, a thorough
    review of all documentation (`README.md`, `/docs`, etc.) must be conducted
    to ensure it is up-to-date with the latest changes.

## Project Structure

The project will be organized into two main directories:

- `backend/`: Houses the Python FastAPI application, including all API logic,
  database models, and background tasks.
- `frontend/`: Contains the Angular workspace for both the management PWA and
  the public-facing e-commerce storefront.

## Key Workflows & Commands

- **Run Backend (Local):** `docker compose up --build`
- **Run Frontend (Local):** `cd frontend && ng serve`
- **Database Migrations:** `docker compose exec backend alembic upgrade head`

## Project Workflow & Organization

All project planning, progress tracking, and task-specific plans are located in
the `/work` directory, which is organized as follows:

- `work/00-project-plan.md`: The high-level project blueprint. This should be
  consulted for the overall vision and architecture.
- `work/current/`: Contains the plan for the **active** development phase and
  the main `PROGRESS.md` log.
- `work/future/`: Contains plans for tasks that are not yet scheduled. The order
  of work in this directory is not guaranteed.
- `work/archive/`: Contains all plans and logs from **completed** phases for
  historical reference.

**Workflow for New Sessions:** To begin a new work cycle, first consult the
`work/current/PROGRESS.md` file to understand the most recent state. Then,
review the active phase plan within the `/work/current` directory to understand
the immediate goals and tasks.

**Formatting:** This project uses Prettier to enforce an 80-character line width
for Markdown files. Please adhere to this when editing documentation.

## Development Principles

To ensure a maintainable and scalable codebase, this project adheres to the
following principles:

1.  **Repository Pattern:** All database interactions are abstracted away from
    the API layer using repositories.
    - A generic `CRUDBase` class provides common CRUD operations.
    - Model-specific repositories (e.g., `crud_product.py`) inherit from
      `CRUDBase` and implement any additional, model-specific logic.
    - API endpoints should be thin and delegate all database logic to the
      repository layer.

2.  **Centralized API Routing:** The API routing for each version is centralized
    in a single file (e.g., `src/api/v1/api.py`).
    - This file is responsible for including all endpoint routers and defining
      their prefixes and tags.
    - The main `main.py` application file should only include the top-level API
      router for each version.

3.  **Security Best Practices:**
    - Passwords are never stored in plaintext. They are hashed using `bcrypt`
      via the `passlib` library.
    - Authentication and authorization mechanisms will be implemented to protect
      sensitive endpoints.

4.  **Efficient Testing:**
    - Database fixtures are session-scoped to improve test performance.
    - Reusable data fixtures are used to keep tests clean and DRY.

## Phased Development Plan

The project is divided into eight distinct phases:

1.  **Phase 1: The Core Foundation & Search Backend:** Establish the backend
    API, database, and semantic search capabilities.
2.  **Phase 2: The Cross-Platform PWA Management App:** Develop the core UI for
    inventory management as a PWA.
3.  **Phase 3: Intelligent Product Ingestion & Indexing:** Automate product
    creation via camera/barcode scanning.
4.  **Phase 4: AI Content Generation & Media Management:** Integrate AI tools
    for creating marketing assets.
5.  **Phase 5: AI-Powered Purchase Order Management:** Streamline inbound
    inventory and receiving workflows.
6.  **Phase 6: Deep Marketplace Integration Engine:** Synchronize products,
    stock, and orders with third-party marketplaces.
7.  **Phase 7: The Hybrid E-commerce Storefront:** Build a public-facing shop
    with direct and marketplace purchase options.
8.  **Phase 8: Advanced Multi-Channel Analytics:** Develop a dashboard for
    analyzing sales data across all channels.

## Testing

The backend is tested using `pytest`. Code quality is enforced with `ruff`.

- **Run all backend tests:**
  ```bash
  docker compose exec backend python -m pytest
  ```
- **Run the backend linter:**
  ```bash
  docker compose exec backend ruff check .
  ```

The frontend is tested using the Web Test Runner with Playwright.

- **Run all frontend tests:**
  ```bash
  npm test --prefix frontend
  ```

These checks are also automated and run on every push and pull request to the
`main` branch using GitHub Actions.

## Documentation Strategy

This project maintains a comprehensive technical documentation hub in the
`/docs` directory. The goal is to provide a single source of truth for
developers to understand the architecture, setup, and development workflows.

When adding a new feature or making a significant change, the corresponding
documentation must be added or updated. Please place new content in the
appropriate thematic directory (`getting-started`, `guides`, `explanation`, or
`reference`) to maintain the organized structure.

## Troubleshooting

### Backend: `relation "products" does not exist`

- **Symptom:** The backend test suite (`npm run test:backend`) fails with a
  `sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "products" does not exist`
  error, even though the migrations appear to be correct.
- **Cause:** This issue can arise from a corrupted or inconsistent Alembic
  migration history. This can happen if you have manually edited migration
  files, or if you have a mix of auto-generated and manually-written migrations.
- **Solution:** The most robust solution is to squash all existing migrations
  into a single file. This will create a clean, consistent history for Alembic
  to follow.
  1.  Read the content of all existing migration files.
  2.  Create a new migration file (e.g., `0001_squashed_migrations.py`) and
      combine the `upgrade()` and `downgrade()` functions from all the old files
      into the new one.
  3.  Delete the old migration files.
  4.  Ensure your `test:backend` script is configured to destroy the old
      database volume before running the tests (e.g., `docker compose down -v`).
      This will ensure that the new, squashed migration is run against a clean
      database.

### Backend: `Can't locate revision identified by '<hash>'` in tests

- **Symptom:** The backend test suite fails with an error like
  `alembic.util.exc.CommandError: Can't locate revision identified by '241bdbf575f5'`
  when running `npm run test:backend`.
- **Cause:** The test database's `alembic_version` table contains a reference to
  a migration revision that no longer exists in the codebase. This can happen 
  after deleting or squashing migration files without properly updating the 
  database state.
- **Solution:** Manually clear the alembic version table and create a fresh 
  migration file that represents the current state of the models:
  1. Connect to the test database and delete records from the `alembic_version` table:
     ```bash
     docker compose exec db-test psql -U fulcrum_test -d fulcrum_test -c "DELETE FROM alembic_version;"
     ```
  2. Create a new migration file that captures the current model state with both 
     `upgrade()` and `downgrade()` functions.
  3. Insert the new revision ID into the `alembic_version` table to establish
     the current state:
     ```bash
     docker compose exec db-test psql -U fulcrum_test -d fulcrum_test -c "INSERT INTO alembic_version (version_num) VALUES ('<new_revision_id>');"
     ```
  4. Run tests again to ensure the alembic upgrade/downgrade cycle works properly.
