# 2. Backend Setup & Local Development

This document provides a guide to setting up and running the backend services
for local development.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

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
    The default values in the `.env` file are configured for the local Docker
    Compose setup and do not need to be changed for development.

## Setting Up a Virtual Environment

For running local scripts, such as the fast backend tests
(`npm run test:backend:fast`) or the documentation server
(`npm run docs:serve`), you need a local Python environment. Using a virtual
environment is a critical best practice to avoid conflicts with system-wide
packages.

1.  **Create the Virtual Environment:**
    From the project root, run:
    ```bash
    python3 -m venv backend/venv
    ```
    This will create a `venv` directory inside the `backend` folder, which is
    already included in `.gitignore`.

2.  **Activate the Virtual Environment:**
    -   **On macOS and Linux:**
        ```bash
        source backend/venv/bin/activate
        ```
    -   **On Windows:**
        ```bash
        .\\backend\\venv\\Scripts\\activate
        ```
    Your shell prompt should now be prefixed with `(venv)`, indicating that the
    virtual environment is active.

3.  **Install Dependencies:**
    Once the environment is active, install all the required packages:
    ```bash
    python3 -m pip install -r backend/requirements.txt
    ```

Now, any `npm` scripts that use `python3` or `pip` will use the versions
installed inside your isolated virtual environment, ensuring a consistent setup.

## Running the Application

All backend services are managed via Docker Compose.

- **Build and Start All Services:** This is the most common command you will
  use. It builds the Docker images (if they don't exist or have changed) and
  starts the `backend`, `db`, `redis`, and `worker` containers.

  ```bash
  # From the project root
  docker compose up --build
  ```

  - Add the `-d` flag (`docker compose up -d --build`) to run the containers in
    detached mode (in the background).

- **Accessing the API:**
  - The API will be running at `http://localhost:8000`.
  - The interactive Swagger UI documentation is available at
    `http://localhost:8000/docs`.
  - The Flower dashboard for monitoring background tasks is at
    `http://localhost:5555`.

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
  command inside a _running_ container. This is how you run tests or migrations.
  ```bash
  # Example: Run the test suite
  docker compose exec backend python -m pytest
  ```

## Default Superuser

On startup, the application will automatically create a default superuser if one
does not already exist. The credentials for this user are configured in the
`.env` file in the `backend` directory.

- **`FIRST_SUPERUSER_EMAIL`**: The email address for the default superuser.
- **`FIRST_SUPERUSER_PASSWORD`**: The password for the default superuser.

The default credentials in `.env.example` are:

- **Email:** `admin@example.com`
- **Password:** `changeme`
