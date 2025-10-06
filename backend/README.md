# Fulcrum Backend

This directory contains the Python FastAPI application that serves as the backend for the Fulcrum platform.

## Overview

The backend is responsible for:
- Providing a RESTful API for all frontend clients.
- Managing the database schema and data.
- Handling business logic for inventory, orders, and marketplaces.
- Interfacing with AI services for tasks like semantic search and content generation.
- Running background tasks using Celery.

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL with pgvector
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Async Tasks:** Celery with Redis
- **Containerization:** Docker & Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose must be installed on your system.

### Running the Application

1.  **Environment Variables:**
    - Copy the `.env.example` file to a new file named `.env`.
    - Review and update the variables in `.env` if necessary (the defaults are suitable for local development).

2.  **Build and Run Containers:**
    - Open a terminal in the root directory of the project (`/fulcrum`).
    - Run the following command:
      ```bash
      docker compose up --build
      ```
    - This will build the Docker image for the backend, pull the required database and Redis images, and start all the services.

3.  **Accessing the API:**
    - The API will be available at `http://localhost:8000`.
    - Interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs`.

## Database Migrations

This project uses Alembic to manage database schema changes.

**Important Note:** There is a known issue with running `alembic` commands via `docker compose exec` due to Docker networking context. The recommended way to run migrations is to use `docker compose run`, which ensures the command runs within the correct network.

### Generating a New Migration

After making changes to the SQLAlchemy models in `src/models/`, you need to generate a new migration script:

```bash
docker compose run --rm backend alembic revision --autogenerate -m "Your descriptive migration message"
```

### Applying Migrations

To apply all pending migrations to the database, run:

```bash
docker compose run --rm backend alembic upgrade head
```

## Project Structure

- `alembic/`: Contains Alembic migration scripts and configuration.
- `src/`: The main source code for the application.
  - `api/`: FastAPI routers and API endpoint definitions.
  - `config.py`: Pydantic settings management.
  - `database.py`: Database connection and session management.
  - `main.py`: The main FastAPI application entrypoint.
  - `models/`: SQLAlchemy database models.
  - `schemas/`: Pydantic data validation schemas.
  - `services/`: Business logic and service abstractions.
- `Dockerfile`: Instructions for building the backend Docker image.
- `requirements.txt`: Python package dependencies.
