# Contributing to Fulcrum

We welcome contributions to Fulcrum, whether it's improving the code, fixing a
bug, or enhancing the documentation. This guide outlines the development
workflow, coding standards, and instructions for working with the documentation
itself.

## Development Workflow

1.  **Fork the repository** and clone it to your local machine.
2.  **Create a new branch** for your feature or bug fix:

    ```bash
    git checkout -b feature/your-feature-name
    ```

3.  **Set up your local development environment** by following the guides for
    the [backend](../getting-started/backend-setup.md) and
    [frontend](../getting-started/frontend-setup.md).
4.  **Make your changes.** Please adhere to the coding style and conventions
    used throughout the project.
5.  **Run local quality checks** using the git hooks that will also run in CI:
    - The **pre-commit** hook runs fast backend tests and linter on your
      changes.
    - The **pre-push** hook runs the full CI test suite (backend, frontend, and
      linting) to ensure comprehensive coverage before pushing code.
6.  **Commit your changes** with a clear and descriptive commit message. We
    follow the [Conventional Commits](https://www.conventionalcommits.org/)
    specification.
7.  **Push your branch** to your fork:

    ```bash
    git push origin feature/your-feature-name
    ```

8.  **Open a pull request** to the `main` branch of the original repository.

## Coding Standards

- **Python Backend:**
  - Follow the PEP 8 style guide.
  - Use type hints for all function signatures.
  - Add docstrings to all modules, classes, and functions to explain their
    purpose.
- **Commit Messages:**
  - Use the Conventional Commits format (e.g., `feat:`, `fix:`, `docs:`,
    `chore:`).
- **Markdown Formatting:**
  - All Markdown files (`.md`) in this project are formatted using Prettier.
  - **VS Code (Recommended):**
    - Install the
      [Prettier - Code formatter](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode)
      extension.
    - The project is pre-configured to format Markdown files automatically on
      save.
  - **Command Line:**
    - To check for formatting issues: `npm run lint:md`
    - To automatically fix formatting issues: `npm run format:md`

## Building with Bazel (Optional)

Fulcrum supports [Bazel](https://bazel.build/) as an alternative build system
for faster incremental builds and reproducible containers.

```bash
# Build frontend and backend
bazel build //frontend:build
bazel build //backend/src:main

# Run tests
bazel test //backend/tests:test_fast_dummy

# Build Docker images
bazel run //frontend/image:frontend_tarball
```

See **[Building with Bazel](./using-bazel.md)** for comprehensive documentation
including Docker integration and troubleshooting.

## Database Management Tools

For local development, we provide several scripts to help manage your database
state. These are located in the `scripts/` directory.

### `scripts/reset_db.sh`

**WARNING: DATA LOSS.** This script completely drops the database, recreates it,
and runs all migrations. Use this when you need a fresh start or if your
migration history is corrupted.

### `scripts/seed_full.py`

This script populates the database with sample data, including:

- Products (reusing existing ones or creating new)
- Marketplaces and Listings
- Marketing Campaigns and Quick Posts

Usage:

```bash
npm run db:reset  # Wipes DB and runs migrations
npm run db:seed   # Seeds data
```

## Contributing to the Documentation

### Tech Stack

The documentation is built using [Sphinx](https://www.sphinx-doc.org/), a
powerful documentation generator, and written in Markdown using the
[MyST parser](https://myst-parser.readthedocs.io/). The site uses the modern
[Furo](https://pradyunsg.me/furo/) theme.

### Local Development Environment

To work on the documentation locally, you must first set up a local Python
development environment for running scripts. We use `uv`, a fast, modern Python
package manager.

1.  **Install `uv`:** `uv` is a single binary that's easy to install.
    - **On macOS, Linux, and Windows (WSL):**

      ```bash
      curl -LsSf https://astral.sh/uv/install.sh | sh
      ```

    - For other installation methods, see the
      [official `uv` documentation](https://astral.sh/uv#installation).

2.  **Create and Activate the Virtual Environment:** From the project root, run:

    ```bash
    # Create the virtual environment in ./backend/venv
    uv venv backend/venv
    # Activate it
    source backend/venv/bin/activate
    ```

    Your shell prompt should now be prefixed with `(venv)`.

3.  **Install Dependencies:** Once the environment is active, install all
    required packages using `uv`.

    ```bash
    uv pip install -r backend/requirements.txt
    ```

### Previewing the Documentation

Once your environment is set up, you can run a live-reloading web server from
the project root:

```bash
npm run docs:serve
```

### Building the Documentation

To build a static version of the documentation (e.g., for deployment), run the
following command from the project root:

```bash
npm run docs:build
```

The static HTML files will be generated in the `docs/_build/html` directory.
