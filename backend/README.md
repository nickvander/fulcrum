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
- **Dependency Management:** UV
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

This project uses Alembic to manage database schema changes. A wrapper script, `migrate.sh`, is provided to simplify the process of running migrations within the Docker container.

### Generating a New Migration

After making changes to the SQLAlchemy models in `src/models/`, you need to generate a new migration script. Run the following command from the project root:

```bash
docker compose exec backend ./migrate.sh revision --autogenerate -m "Your descriptive migration message"
```

### Applying Migrations

To apply all pending migrations to the database, run:

```bash
docker compose exec backend ./migrate.sh upgrade head
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
