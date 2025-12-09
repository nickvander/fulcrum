# Building with Bazel

Fulcrum supports building with [Bazel](https://bazel.build/), a fast and
scalable build system from Google. This guide covers how to use Bazel for
building and testing the Fulcrum project.

## Overview

Bazel provides several benefits over traditional build systems:

- **Incremental Builds**: Only rebuilds what changed
- **Reproducible**: Same inputs always produce same outputs
- **Scalable**: Efficient caching and parallel execution
- **Multi-Language**: Single build system for Python, TypeScript, and Docker

## Installation

### Install Bazelisk (Recommended)

Bazelisk automatically downloads and uses the correct Bazel version:

```bash
# macOS
brew install bazelisk

# Linux
npm install -g @bazel/bazelisk

# Windows
choco install bazelisk
```

### Verify Installation

```bash
bazel --version
# Should output: bazel 8.4.2
```

## Basic Usage

### Building

```bash
# Build FastAPI application
bazel build //backend/src:main

# Build Celery worker
bazel build //backend/src:celery_worker

# Build multiple targets
bazel build //backend/src:main //backend/src:celery_worker
```

The built binaries are placed in `bazel-bin/backend/src/`.

### Testing

```bash
# Run a specific test
bazel test //backend/tests:test_fast_dummy

# Show all test output
bazel test //backend/tests:test_fast_dummy --test_output=all

# Run all backend tests
bazel test //backend/tests:all_backend_tests
```

### Dependency Management

```bash
# View the dependency graph
bazel mod graph

# Query specific dependencies
bazel query "deps(//backend/src:main)"

# Show all targets
bazel query //...
```

## Docker Integration

Bazel can build Docker containers using `rules_oci`, providing better caching and reproducibility than traditional Dockerfiles.

### Building Container Images

```bash
# Build backend Docker image
bazel build //backend/image:backend_image

# Build frontend Docker image
bazel build //frontend/image:frontend_image

# Load images into Docker daemon
bazel run //backend/image:backend_tarball
bazel run //frontend/image:frontend_tarball

# Verify the images
docker images | grep fulcrum
# fulcrum/backend   latest  ...  124MB
# fulcrum/frontend  latest  ...  54.5MB
```

### Using with Docker Compose

The project includes `docker-compose.bazel.yml` for using Bazel-built images:

```bash
# Build the frontend image
bazel run //frontend/image:frontend_tarball

# Start services (frontend from Bazel, backend from traditional Docker)
docker compose -f docker-compose.bazel.yml up
```

### Local Development (Recommended)

For local development, use the traditional docker-compose for backend and `ng serve`
for frontend. This gives you the best experience with hot reloading and API proxy:

```bash
# 1. Start backend services
docker compose up -d db redis backend

# 2. Run migrations
docker compose exec backend alembic upgrade head

# 3. Start frontend with dev server (in another terminal)
cd frontend && pnpm ng serve
```

This gives you:
- **Frontend**: http://localhost:4200 (with hot reload + API proxy)
- **Backend API**: http://localhost:8000

### Production Containers

For production, use the Bazel-built frontend container:

```bash
# Build the Bazel frontend image
bazel run //frontend/image:frontend_tarball

# The image is: fulcrum/frontend:latest (~55MB nginx-alpine)
```

> [!WARNING]
> **Frontend Container Networking Limitation**: The Bazel-built frontend container
> uses nginx to proxy `/api/` requests to the backend. However, when running from
> `docker-compose.bazel.yml` while the backend runs from `docker-compose.yml`,
> they are on different Docker networks and cannot communicate. For local
> development, use `ng serve` which has a working API proxy. The Bazel frontend
> container is designed for production deployments where networking is configured
> at the infrastructure level.

> [!WARNING]
> **Frontend Tests Blocked**: `bazel test //frontend:test` is currently failing due to `sass-embedded` compilation issues within the Bazel sandbox. Use `ng test` for frontend unit testing until this is resolved.

> [!NOTE]
> The Bazel backend container has a `py_binary` runfiles issue. Use traditional
> Docker for backend until this is resolved with `rules_pex`.

### Container Build Configuration

#### Backend Container

The backend container is defined in `backend/image/BUILD.bazel`:

```starlark
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_tar(
    name = "app_layer",
    srcs = ["//backend/src:main"],
    package_dir = "/app",
)

oci_image(
    name = "backend_image",
    base = "@python_base",
    tars = [":app_layer"],
    entrypoint = ["/app/main"],
)

oci_load(
    name = "backend_tarball",
    image = ":backend_image",
    repo_tags = ["fulcrum/backend:latest"],
)
```

#### Frontend Container

The frontend container is defined in `frontend/image/BUILD.bazel`:

```starlark
pkg_tar(
    name = "app_layer",
    srcs = ["//frontend:build"],
    package_dir = "/usr/share/nginx/html",
    strip_prefix = "dist/frontend/browser",
)

pkg_tar(
    name = "config_layer",
    srcs = ["nginx.conf"],
    package_dir = "/etc/nginx/conf.d",
    remap_paths = {"nginx.conf": "default.conf"},
)

oci_image(
    name = "frontend_image",
    base = "@nginx_base",
    tars = [":app_layer", ":config_layer"],
    exposed_ports = ["80/tcp"],
)

oci_load(
    name = "frontend_tarball",
    image = ":frontend_image",
    repo_tags = ["fulcrum/frontend:latest"],
)
```

### Benefits of Bazel Docker Builds

- **Better Caching**: Layer changes are detected more accurately
- **Reproducible**: Same inputs always produce identical images  
- **Faster Rebuilds**: Only changed layers are rebuilt
- **Integrated**: Uses the same dependency graph as code builds


## Build Configuration

### MODULE.bazel

Fulcrum uses **Bzlmod**, Bazel's modern dependency management system. All
external dependencies are declared in `MODULE.bazel`:

```starlark
bazel_dep(name = "rules_python", version = "1.0.0")
bazel_dep(name = "aspect_rules_js", version = "2.1.0")
bazel_dep(name = "aspect_rules_ts", version = "3.2.0")
bazel_dep(name = "rules_oci", version = "2.0.0")
```

### .bazelrc

Build options are configured in `.bazelrc`:

- `--verbose_failures`: Show detailed error messages
- `--test_output=errors`: Only show failing test output

### .bazelignore

The following directories are excluded from Bazel scanning:

- `node_modules/`
- `.venv/`
- `backend/venv/`

## Project Structure

```
fulcrum/
├── MODULE.bazel              # Bzlmod dependency configuration
├── .bazelrc                  # Build options
├── .bazelversion             # Pin Bazel version (8.4.2)
├── BUILD.bazel               # Root build file
│
├── backend/
│   ├── BUILD.bazel           # Expose requirements files
│   ├── requirements_lock.txt # Pinned Python dependencies
│   ├── src/
│   │   └── BUILD.bazel       # py_library + py_binary rules
│   └── tests/
│       └── BUILD.bazel       # py_test rules
│
└── frontend/
    ├── BUILD.bazel           # Expose pnpm-lock.yaml
    └── pnpm-lock.yaml        # Pinned npm dependencies
```

## Common Commands

### Building

```bash
# Build specific target
bazel build //backend/src:main

# Build all targets in a package
bazel build //backend/src:all

# Clean build cache
bazel clean

# Deep clean (removes all cached artifacts)
bazel clean --expunge
```

### Testing

```bash
# Run specific test
bazel test //backend/tests:test_fast_dummy

# Show all test output
bazel test //backend/tests:test_fast_dummy --test_output=all

# Run tests with specific tag
bazel test //backend/tests:all --test_tag_filters=fast

# Run tests matching pattern
bazel test //backend/tests:test_*
```

### Querying

```bash
# Show all targets
bazel query //...

# Show dependencies of a target
bazel query "deps(//backend/src:main)"

# Show tests in a package
bazel query "kind(py_test, //backend/tests:all)"

# Show dependency graph
bazel mod graph
```

## Integration with Docker Compose

Bazel runs **alongside** the existing Docker Compose workflow. You can choose
which build system to use based on your needs:

### Docker Compose

```bash
docker compose up --build
docker compose exec backend python -m pytest
cd frontend && npm test
```

### Bazel

```bash
bazel build //backend/src:main
bazel test //backend/tests:all_backend_tests
```

### When to Use Which?

| Use Docker Compose When...            | Use Bazel When...                   |
| ------------------------------------- | ----------------------------------- |
| Running full development environment  | Building specific components        |
| Need database and Redis               | Running unit tests                  |
| Debugging integration issues          | Checking build performance          |
| Local development with hot reload     | Verifying dependency changes        |
| E2E testing                           | CI/CD builds                        |
| First time setup                      | Incremental builds after code edits |

## Troubleshooting

### "no such package" errors

Make sure the directory has a `BUILD.bazel` file. Bazel only recognizes
directories with BUILD files as packages.

### "Cannot find module" in Python

Check that the `imports` attribute in your `py_library` or `py_test` includes
the correct path (usually `[".."]` or `["../.."]`).

### Build is slow

Try these optimizations:

```bash
# Enable remote caching (if configured)
bazel build --config=remote

# Use more parallel jobs
bazel build --jobs=8
```

## Resources

- [Bazel Documentation](https://bazel.build/docs)
- [rules_python](https://github.com/bazelbuild/rules_python)
- [aspect_rules_js](https://github.com/aspect-build/rules_js)
- [rules_oci](https://github.com/bazel-contrib/rules_oci)
- [Bzlmod Documentation](https://bazel.build/external/overview#bzlmod)
