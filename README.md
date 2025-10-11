# Fulcrum

Fulcrum is an AI-first commerce hub designed to streamline the entire product lifecycle, from inventory and supplier management to multi-channel sales and business analytics.

## Documentation

All technical documentation for the project, including architecture, setup guides, and contribution workflows, is located in our **[Sphinx Documentation Hub](docs/source/introduction.md)**.

This is the central source of truth for developers.

### Key Documentation

- **[Architecture Overview](docs/source/concepts/architecture.md)**
- **[Backend Setup Guide](docs/source/getting-started/backend-setup.md)**
- **[Frontend Setup Guide](docs/source/getting-started/frontend-setup.md)**
- **[Contributor Guide](docs/source/guides/contributing.md)**
- **[Testing & CI Guide](docs/source/guides/testing-and-ci.md)**


## Quick Start

### Prerequisites

- Docker
- Docker Compose

### Running the Application

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

The backend API will be available at `http://localhost:8000`. For detailed setup instructions, please see the **[Getting Started](docs/source/getting-started/backend-setup.md)** guide.