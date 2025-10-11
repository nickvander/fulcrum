# Solution Architecture

This document outlines the high-level architecture of the Fulcrum backend and
the key design patterns used.

## Containerization & Orchestration

The entire backend is containerized using Docker and orchestrated with Docker
Compose. This approach provides several key benefits:

- **Consistency:** The application runs in the exact same environment in
  development, testing, and production.
- **Isolation:** Services (backend, database, worker) are isolated from each
  other and the host machine.
- **Portability:** The entire stack can be run on any machine with Docker
  installed.

### Multi-Stage Dockerfile

The `backend/Dockerfile` uses a **multi-stage build** to create a final
production image that is small and secure.

1.  **Builder Stage:** A temporary `builder` image is created. It installs `uv`
    (a fast package installer) and uses it to compile and install all Python
    dependencies from `requirements.txt` into a virtual environment
    (`/app/venv`).
2.  **Final Stage:** A new, clean Python image is started. It copies _only_ the
    virtual environment from the `builder` stage and the application source code
    from `src/`.

This ensures that build-time tools like `uv` and the package cache are not
included in the final image, reducing its size and attack surface.

## Application Design

The backend is a FastAPI application designed with a clean, layered
architecture.

### Repository Pattern

To avoid duplicating code and to separate database logic from the API layer, we
use the **Repository Pattern**.

- **`CRUDBase` (`src/crud/base.py`):** A generic class that provides standard
  Create, Read, Update, Delete (CRUD) methods. It is designed to work with any
  SQLAlchemy model and Pydantic schema.
- **Specific Repositories (`src/crud/crud_product.py`):** For each SQLAlchemy
  model, we create a specific repository class that inherits from `CRUDBase`.
  This is where any model-specific query logic (e.g., a complex search function)
  would be added in the future.

### API Layer

The API layer (`src/api/`) is responsible for handling HTTP requests and
responses.

- **Thin Endpoints:** Thanks to the repository pattern, the API endpoints are
  very "thin." Their only job is to:
  1.  Receive a request.
  2.  Call the appropriate repository method.
  3.  Return the result.
- This separation of concerns makes the API easy to read, test, and maintain.

### Service Layer & Dependency Injection

To handle business logic that is separate from the database (e.g., calling an
external AI API), we use a **Service Layer**.

- **Abstract Base Classes (`src/services/base.py`):** We define abstract base
  classes for our services (e.g., `AIService`). This defines a clear contract
  for what the service must do, without tying it to a specific implementation.
- **Dependency Injection (`src/api/dependencies.py`):** We use FastAPI's
  built-in dependency injection system (`Depends`) to provide service
  implementations to the API endpoints. This makes the system highly modular and
  easy to test, as we can easily inject a mock service during testing.

### Asynchronous Tasks

For long-running operations (like calling an AI service to generate an
embedding), we use Celery.

- When a product is created, the API endpoint calls
  `generate_product_embedding.delay()`.
- This places a "task" onto a message queue (managed by Redis).
- A separate `worker` container is constantly listening to this queue. It picks
  up the task and executes it in the background, allowing the API to return a
  response to the user immediately.
