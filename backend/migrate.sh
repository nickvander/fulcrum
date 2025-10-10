#!/bin/sh

# This script provides a reliable way to run Alembic migrations
# or the test suite within the Docker container, ensuring that
# environment variables and the virtual environment are correctly loaded.

set -e

# Activate the virtual environment
if [ -f "/app/venv/bin/activate" ]; then
    . /app/venv/bin/activate
else
    echo "Virtual environment not found. Skipping activation."
fi

# Change to the directory where the script is located to ensure alembic.ini is found
cd "$(dirname "$0")"

# The `dotenv` command is not available, so we will manually
# export the DATABASE_URL. The python script `env.py` will
# still load the full .env file.
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check the first argument to decide what to run
if [ "$1" = "test" ]; then
    # Shift the arguments to remove "test" and pass the rest to pytest
    shift
    pytest "$@"
else
    # Execute the alembic command with all arguments passed to this script
    alembic -c /app/alembic.ini "$@"
fi
