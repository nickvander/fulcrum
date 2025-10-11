# Fulcrum

AI-centric inventory management and marketplace management.

This repository contains the source code for the Fulcrum platform, an AI-first
commerce hub designed to streamline the entire product lifecycle.

## Documentation

For detailed technical documentation, including the project architecture, setup
guides, and development workflows, please see our **[Documentation Hub](./docs/README.md)**.

This guide also contains instructions on how to build and serve the documentation
locally.

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
      **[Frontend Setup Guide](./docs/source/frontend-setup.md)**.

4.  **Build and start the services:**
    - From the root directory of the project, run:

    ```bash
    docker compose up --build
    ```

    - This will build the necessary Docker images and start all services. The
      API will be available at `http://localhost:8000`.

## Testing

The project includes a comprehensive test suite for both the backend and
frontend. For detailed instructions on the testing strategy and how to run the
tests, please see the
**[Testing Strategy & CI/CD Guide](./docs/source/testing-and-ci.md)**.

## Contributing

We welcome contributions to Fulcrum! For information on how to set up a local
development environment, our coding standards, and the submission process, please
see our **[Contributor Guide](./CONTRIBUTING.md)**.
