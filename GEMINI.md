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
- **Deployment:** Docker & Docker Compose for the backend, static hosting for the e-commerce frontend.

## Development Principles

-   **Frontend Testing:** The frontend application uses the Web Test Runner for unit testing. All new components and services must be accompanied by a corresponding `.spec.ts` file with adequate test coverage.
-   **Markdown Formatting:** All Markdown files (`.md`) in this project are formatted using Prettier. Before committing any changes to documentation, run `npm run format:md` to ensure consistency.

## Project Structure

The project will be organized into two main directories:

- `backend/`: Houses the Python FastAPI application, including all API logic,
  database models, and background tasks.
- `frontend/`: Contains the Angular workspace for both the management PWA and
  the public-facing e-commerce storefront.

## Key Workflows & Commands

- **Run Backend (Local):** `docker-compose up --build`
- **Run Frontend (Local):** `cd frontend && ng serve`
- **Database Migrations:** `docker-compose exec backend alembic upgrade head`

## Project Workflow & Organization

All project planning, progress tracking, and task-specific plans are located in
the `/work` directory.

- `work/00-project-plan.md`: The high-level project blueprint.
- `work/PROGRESS.md`: A log of completed work for each phase.
- `work/[number]-[task-name].md`: Detailed, actionable plans for specific tasks
  or refactors.

**Workflow for New Sessions:** To begin a new work cycle, first consult
`work/PROGRESS.md` to understand the current state. Then, identify the next open
task file in the `/work` directory (e.g., `work/01-refactor-phase-one.md`), read
the plan, and begin execution.

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

- **Run all tests:**
  ```bash
  docker compose exec backend python -m pytest
  ```
- **Run the linter:**
  ```bash
  docker compose exec backend ruff check .
  ```

These checks are also automated and run on every push and pull request to the
`main` branch using GitHub Actions.

## Documentation Strategy

This project uses the `/docs` directory to store detailed technical
documentation. The goal is to provide a comprehensive resource for developers to
understand the architecture, setup, and development workflows.

When adding a new, significant feature, please consider adding or updating a
corresponding document in the `/docs` directory. This ensures that the
documentation evolves alongside the codebase.
