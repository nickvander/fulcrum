#!/bin/bash
# scripts/reset_db.sh
# Quickly reset the database state for testing.

echo "⚠️  WARNING: This will DESTROY all data in the local database!"
read -p "Are you sure? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo "🔄 Resetting Database..."

# Option 1: Using Alembic to downgrade (cleaner if migrations are perfect)
# docker compose exec backend alembic downgrade base
# docker compose exec backend alembic upgrade head

# Option 2: Brute force recreation (faster/safer for "ensure empty")
# We'll use a python script inside the container to drop all tables and let alembic recreate them
cat <<EOF > backend/src/reset_db_internal.py
from src.database.session import engine
from src.models.base import Base
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_db():
    with engine.connect() as conn:
        logger.info("Dropping all tables...")
        # Disable foreign key checks to avoid ordering issues
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()
    logger.info("Database cleared.")

if __name__ == "__main__":
    reset_db()
EOF

# Copy script is not needed since we mount the volume, but let's just run it via python -m
# Assuming backend volume mount is active and maps locally. 
# If not, we might need to `docker cp`. 
# Let's assume standard dev setup where `backend/` is mounted.

echo "🗑️  Dropping Schema..."
docker compose exec backend python src/reset_db_internal.py

echo "🏗️  Running Migrations..."
docker compose exec backend alembic upgrade head

echo "✨ Database successfully reset!"
