# Documentation Overview

Welcome to the technical documentation for the Fulcrum project. This collection
of documents provides a deep dive into the architecture, setup, and development
workflows for the platform.

## Table of Contents

- **[Solution Architecture](./architecture.md)**
  - An overview of the containerized setup, the multi-stage Dockerfile, the
    repository pattern, and the use of asynchronous tasks.

- **[Backend Setup & Local Development](./backend-setup.md)**
  - A step-by-step guide to getting the backend running on your local machine.

- **[Database Migrations with Alembic](./database-migrations.md)**
  - An explanation of the database migration workflow using the `migrate.sh`
    script.

- **[Testing Strategy & CI/CD](./testing-and-ci.md)**
  - Details on how to write and run tests, use the linter, and how the GitHub
    Actions CI pipeline works.
