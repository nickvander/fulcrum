# Fulcrum

AI-centric inventory management and marketplace management.

This repository contains the source code for the Fulcrum platform, an AI-first
commerce hub designed to streamline the entire product lifecycle.

## Documentation

For detailed technical documentation on the project architecture, setup, and
development workflows, please see the
**[Technical Documentation Hub](./docs/README.md)**.

## Getting Started

This project is containerized using Docker. All services for the backend (API,
database, background workers) are managed via Docker Compose.

### Prerequisites

- Docker
- Docker Compose

### Running the Application

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/nickvander/fulcrum.git
    cd fulcrum
    ```

2.  **Backend Setup:**
    - Navigate to the `backend` directory.
    - Copy the `.env.example` file to a new file named `.env`. The default
      values are configured for local development.

    ```bash
    cd backend
    cp .env.example .env
    cd ..
    ```

3.  **Frontend Setup:**
    - The frontend is an Angular application located in the `frontend/`
      directory.
    - For detailed instructions on installing dependencies and running the
      development server, please see the
      **[Frontend Setup Guide](./docs/frontend-setup.md)**.

4.  **Build and start the services:**
    - From the root directory of the project, run:
    ```bash
    docker compose up --build
    ```

    - This will build the necessary Docker images and start all services. The
      API will be available at `http://localhost:8000`.

## How to Contribute

We welcome contributions to Fulcrum! Please follow these guidelines to ensure a
smooth development process.

### Development Workflow

1.  **Fork the repository** and clone it to your local machine.
2.  **Create a new branch** for your feature or bug fix:
    `git checkout -b feature/your-feature-name`.
3.  **Make your changes.** Please adhere to the coding style and conventions
    used throughout the project.
4.  **Commit your changes** with a clear and descriptive commit message. We
    follow the [Conventional Commits](https://www.conventionalcommits.org/)
    specification.
5.  **Push your branch** to your fork:
    `git push origin feature/your-feature-name`.
6.  **Open a pull request** to the `main` branch of the original repository.

### Key Commands

- **Start all services:** `docker compose up --build`
- **Stop all services:** `docker compose down`
- **Run a command in the backend container:**
  `docker compose exec backend <your-command>`
- **View logs for all services:** `docker compose logs -f`
- **View logs for a specific service:** `docker compose logs -f backend`

### Database Migrations

The project uses Alembic to manage database schema migrations.

- **Generate a new migration script** after changing a model in
  `backend/src/models/`:
  ```bash
  docker compose exec backend alembic revision --autogenerate -m "Your migration message"
  ```
- **Apply all pending migrations:**
  ```bash
  docker compose exec backend alembic upgrade head
  ```
  _(Note: There is a known issue with the `exec` command in some WSL2
  environments. If you encounter DNS or connection errors, please see the
  `backend/README.md` for potential workarounds.)_

### Coding Standards

- **Python Backend:**
  - Follow the PEP 8 style guide.
  - Use type hints for all function signatures.
  - Add docstrings to all modules, classes, and functions to explain their
    purpose.
- **Commit Messages:**
  - Use the Conventional Commits format (e.g., `feat:`, `fix:`, `docs:`,
    `chore:`).
- **Markdown Formatting:**
  - All Markdown files (`.md`) in this project are automatically formatted
    using Prettier to ensure a consistent line length and style.
  - Before committing any changes to Markdown files, please run the formatter.
  - **To check for formatting issues:**
    ```bash
    npm run lint:md
    ```
  - **To automatically fix formatting issues:**
    ```bash
    npm run format:md
    ```
