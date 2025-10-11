# Solution Architecture

This document outlines the high-level architecture of the Fulcrum platform, covering both the backend and frontend applications and the key design patterns used.

## Containerization & Orchestration

The entire backend is containerized using Docker and orchestrated with Docker Compose. This approach provides several key benefits:

- **Consistency:** The application runs in the exact same environment in development, testing, and production.
- **Isolation:** Services (backend, database, worker) are isolated from each other and the host machine.
- **Portability:** The entire stack can be run on any machine with Docker installed.

### Multi-Stage Dockerfile

The `backend/Dockerfile` uses a **multi-stage build** to create a final production image that is small and secure.

1.  **Builder Stage:** A temporary `builder` image is created. It installs all Python dependencies from `requirements.txt` into a virtual environment (`/app/venv`).
2.  **Final Stage:** A new, clean Python image is started. It copies _only_ the virtual environment from the `builder` stage and the application source code from `src/`.

This ensures that build-time tools and package caches are not included in the final image, reducing its size and attack surface.

---

## Backend Architecture

The backend is a FastAPI application designed with a clean, layered architecture to ensure a separation of concerns.

### API Layer & Routing

The API layer (`src/api/`) is responsible for handling HTTP requests and responses.

- **Centralized Routing:** All API v1 routes are aggregated in `src/api/v1/api.py`. This file includes the routers from the `endpoints` directory, providing a single source of truth for the API's structure. The main application (`src/main.py`) then includes this top-level router.
- **Thin Endpoints:** Thanks to the repository and service patterns, the API endpoints are very "thin." Their only job is to handle request validation, call the appropriate business logic, and return a response.

### Business Logic: Services & Repositories

To separate database logic from other business logic, the application uses a combination of the Repository and Service patterns.

- **Repository Pattern (`src/crud/`):**
  - **`CRUDBase` (`src/crud/base.py`):** A generic class that provides standard Create, Read, Update, Delete (CRUD) methods. It is designed to work with any SQLAlchemy model and Pydantic schema.
  - **Specific Repositories (e.g., `src/crud/crud_product.py`):** For each SQLAlchemy model, we create a specific repository class that inherits from `CRUDBase`. This is where any model-specific query logic (e.g., a complex vector search) is implemented.

- **Service Layer (`src/services/`):**
  - This layer handles business logic that is independent of the database, such as calling an external AI API.
  - **Abstract Base Classes (`src/services/base.py`):** We define abstract base classes for our services (e.g., `AIService`). This defines a clear contract for what the service must do.
  - **Dependency Injection (`src/api/dependencies.py`):** We use FastAPI's built-in dependency injection system (`Depends`) to provide service implementations to the API endpoints. This makes the system highly modular and easy to test, as we can easily inject a mock service during testing.

### Asynchronous Tasks with Celery

For long-running operations that should not block the API response (like generating a product embedding), we use Celery.

- When a product is created, the API endpoint calls `generate_product_embedding.delay()` (`src/tasks.py`).
- This places a "task" onto a message queue (managed by Redis).
- A separate `worker` container, defined in `docker-compose.yml`, runs a Celery worker process (`src/celery_worker.py`) that listens to this queue. It picks up the task and executes it in the background.

---

## Frontend Architecture

The frontend application is built with Angular and follows a modular, feature-based architecture to ensure a clean separation of concerns and scalability.

### Core Modules & Services

- **`CoreModule` (`src/app/core/`):** This module provides singleton services and core layout components that are used application-wide. This includes the main `HeaderComponent` and `SidenavComponent`. It is also where application-wide HTTP interceptors for loading spinners and error handling are provided.
- **`SharedModule` (`src/app/shared/`):** This module contains reusable components, directives, and pipes that can be imported and used by multiple feature modules. The `AiSearchBarComponent` is a good example.

### Feature Modules

Each primary feature of the application is encapsulated within its own module. This makes the codebase easier to maintain and allows for lazy loading, which improves initial application load times.

- **`AuthModule` (`src/app/auth/`):**
  - **Purpose**: Handles all user authentication logic.
  - **Key Components**: `LoginComponent`
  - **Key Services**: `AuthService` (manages JWT tokens), `AuthGuard` (protects routes), `AuthInterceptor` (attaches auth headers to API requests).

- **`ProductsModule` (`src/app/products/`):**
  - **Purpose**: Manages the full CRUD lifecycle for products.
  - **Key Components**: `ProductListComponent`, `ProductFormComponent`, and the `ProductIngestionComponent` for camera-based intake.
  - **Key Services**: `ProductService` (handles all API interactions for products).

### Progressive Web App (PWA)

The application is a fully-featured PWA, enabled by the `@angular/pwa` package.

- **Service Worker (`ngsw-config.json`):** Caches network requests and application assets, allowing for offline or low-connectivity access.
- **Web App Manifest (`manifest.webmanifest`):** Provides metadata that allows users to "install" the application to their home screen on mobile and desktop devices for a native-like experience.