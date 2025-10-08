#!/bin/sh

# This script provides a reliable way to run Alembic migrations
# within the Docker container, ensuring that environment variables
# from the .env file are correctly loaded.

set -e

# Change to the directory where the script is located to ensure alembic.ini is found
cd "$(dirname "$0")"

# The `dotenv` command is not available, so we will manually
# export the DATABASE_URL. The python script `env.py` will
# still load the full .env file.
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Execute the alembic command with all arguments passed to this script
alembic -c /app/alembic.ini "$@"
