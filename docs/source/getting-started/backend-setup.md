# Backend Setup & Local Development

This document provides a guide to setting up and running the backend services
for local development using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

For Debian/Ubuntu-based systems, you can install them with the following
command:

```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose
```

## First-Time Setup

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/nickvander/fulcrum.git
    cd fulcrum
    ```

2.  **Environment File:** The project uses a `.env` file to manage environment
    variables for the backend. This file is ignored by Git, so you must create
    it.

    ```bash
    # From the project root
    cp backend/.env.example backend/.env
    ```

    The default values in this file are suitable for local development. For a
    detailed explanation of all the variables, see the
    [**Configuration Reference**](../reference/configuration.md).

## Running the Application

All backend services are managed via the `docker-compose.yml` file at the root
of the project.

- **Build and Start All Services:** This is the most common command you will
  use. It builds the Docker images (if they don't exist or have changed) and
  starts the `backend`, `db`, `redis`, `worker`, and `flower` containers.

  ```bash
  # From the project root
  docker compose up --build
  ```

  - Add the `-d` flag (`docker compose up -d --build`) to run the containers in
    detached mode (in the background).

- **Accessing Services:**
  - **API:** The API will be running at `http://localhost:8000`.
  - **Interactive Docs:** The interactive Swagger UI documentation is available
    at `http://localhost:8000/docs`.
  - **Task Monitoring:** The Flower dashboard for monitoring background tasks is
    at `http://localhost:5555`.

## Common Docker Compose Commands

- **Stop All Services:**

  ```bash
  docker compose down
  ```

- **View Logs:**

  ```bash
  # View logs for all running services
  docker compose logs -f

  # View logs for a specific service (e.g., the backend)
  docker compose logs -f backend
  ```

- **Run a Command Inside a Container:** Use `docker compose exec` to run a
  command inside a _running_ container. This is the standard way to run tests or
  database migrations.

  ```bash
  # Example: Run the test suite
  docker compose exec backend python -m pytest
  ```

## Default Superuser

On startup, the application will automatically create a default superuser if one
does not already exist. The credentials for this user are configured in the
`.env` file. See the
[**Configuration Reference**](../reference/configuration.md) for more details.
