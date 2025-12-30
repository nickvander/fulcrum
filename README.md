# Fulcrum

Fulcrum is an AI-first commerce hub designed to streamline the entire product
lifecycle, from inventory and supplier management to multi-channel sales and
business analytics.

## Documentation

All technical documentation for the project, including architecture, setup
guides, and contribution workflows, is located in our
**[Sphinx Documentation Hub](docs/introduction.md)**.

This is the central source of truth for developers.

### Key Documentation

- **[Architecture Overview](docs/concepts/architecture.md)**
- **[Backend Setup Guide](docs/getting-started/backend-setup.md)**
- **[Frontend Setup Guide](docs/getting-started/frontend-setup.md)**
- **[Contributor Guide](docs/guides/contributing.md)**
- **[Testing & CI Guide](docs/guides/testing-and-ci.md)**

## Quick Start

### Prerequisites

- Docker
- Docker Compose

### Running the Application

#### Backend

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/nickvander/fulcrum.git
    cd fulcrum
    ```

2.  **Set up environment variables:**

    ```bash
    cp backend/.env.example backend/.env
    ```

3.  **Build and start all services:**

    ```bash
    docker compose up --build
    ```

4.  **Run database migrations:** Open a new terminal and run:
    ```bash
    docker compose exec backend alembic upgrade head
    ```

The backend API will be available at `http://localhost:8000`.

#### Frontend

1.  **Navigate to the frontend directory:**

    ```bash
    cd frontend
    ```

2.  **Install dependencies:**

    ```bash
    npm install
    ```

**Start the development server:**

    ```bash
    npm start
    ```

The frontend application will be available at `http://localhost:4200`.

## Building with Bazel (Optional)

Fulcrum supports building with [Bazel](https://bazel.build/) as an alternative
build system for improved build performance and reproducibility.

### Prerequisites

- [Bazelisk](https://github.com/bazelbuild/bazelisk) (recommended) or Bazel
  8.4.2+
- pnpm (for frontend dependencies)

### Quick Start

```bash
# Build backend
bazel build //backend/src:main
bazel build //backend/src:celery_worker

# Build frontend
bazel build //frontend:build

# Run backend tests
bazel test //backend/tests:test_fast_dummy

# Build Docker images
bazel run //backend/image:backend_tarball   # Loads fulcrum/backend:latest
bazel run //frontend/image:frontend_tarball # Loads fulcrum/frontend:latest

# Check dependency graph
bazel mod graph
```

**Note:** Bazel runs alongside Docker Compose. You can use either build system
based on your needs. See
[docs/guides/using-bazel.md](docs/guides/using-bazel.md) for comprehensive
documentation including Docker integration.

For detailed setup instructions, please see the
**[Getting Started](docs/getting-started/backend-setup.md)** guide.
