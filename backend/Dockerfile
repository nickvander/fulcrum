# --- Builder Stage ---
# This stage installs dependencies into a virtual environment.
FROM python:3.11-slim as builder

WORKDIR /app

# Copy only the requirements file to leverage Docker cache
COPY requirements.txt .

# Create a virtual environment and install dependencies into it
RUN python -m pip install --upgrade pip && \
    python -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# --- Final Stage ---
# This stage creates the final, smaller production image.
FROM python:3.11-slim

# Install PostgreSQL client for pg_isready
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user and group first
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID -r appgroup && useradd -u $UID -g appgroup -r appuser

# Copy the virtual environment from the builder stage with correct ownership
COPY --from=builder --chown=appuser:appgroup /app/venv /app/venv

# Copy the application source code with correct ownership
COPY --chown=appuser:appgroup ./src /app/src

# Create and set permissions for the uploads directory
RUN mkdir -p /app/uploads && chown -R appuser:appgroup /app/uploads

# Create and set permissions for the ruff cache directory
RUN mkdir -p /app/.ruff_cache && chown -R appuser:appgroup /app/.ruff_cache

# Create and set permissions for the pytest cache directory
RUN mkdir -p /app/.pytest_cache && chown -R appuser:appgroup /app/.pytest_cache

# Switch to the non-root user
USER appuser

# Activate the virtual environment for subsequent commands
ENV PATH="/app/venv/bin:$PATH"

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
