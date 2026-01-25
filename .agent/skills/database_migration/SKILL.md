---
name: Database Migration
description: Safely handle database schema changes using Alembic, including troubleshooting common migration issues.
---

# Database Migration Skill

You are a database administrator for the Fulcrum project. Your role is to safely
manage schema changes using Alembic.

## When to Use This Skill

Use this skill when:
- Adding new tables or columns.
- Modifying existing schema.
- Troubleshooting migration errors.

---

## Standard Migration Workflow

### Step 1: Modify the Model

Edit the SQLAlchemy model in `backend/src/models/`.

**Model Pattern:**
```python
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.models.base import Base

class EntityName(Base):
    __tablename__ = "entity_names"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Register in `models/__init__.py`:**
```python
from .entity import EntityName  # noqa: F401
```

### Step 2: Generate Migration

```bash
docker compose exec backend alembic revision --autogenerate -m "add entity_names table"
```

### Step 3: Review Migration File

**CRITICAL**: Always inspect the generated file in `backend/src/alembic/versions/`.

**Check for:**
- Correct `upgrade()` operations (CREATE TABLE, ADD COLUMN).
- Correct `downgrade()` operations (DROP TABLE, DROP COLUMN).
- No unintended changes to other tables.
- Proper handling of nullable constraints.

### Step 4: Apply Migration

```bash
docker compose exec backend alembic upgrade head
```

### Step 5: Verify

```bash
docker compose exec backend python -m pytest
```

---

## Common Issues and Solutions

### Issue 1: `relation "table_name" does not exist`

**Symptom**: Tests fail with `ProgrammingError: relation does not exist`.

**Cause**: Corrupted or inconsistent Alembic migration history.

**Solution - Squash Migrations:**

1. Read all existing migration files in `backend/src/alembic/versions/`.
2. Create a new file (e.g., `0001_squashed.py`) combining all `upgrade()`
   and `downgrade()` logic.
3. Delete all old migration files.
4. Reset the database:
   ```bash
   docker compose down -v
   docker compose up -d
   docker compose exec backend alembic upgrade head
   ```

---

### Issue 2: `Can't locate revision identified by '<hash>'`

**Symptom**: `CommandError: Can't locate revision`.

**Cause**: `alembic_version` table references a deleted migration.

**Solution - Reset Alembic State:**

```bash
# Clear version table
docker compose exec db-test psql -U fulcrum_test -d fulcrum_test \
  -c "DELETE FROM alembic_version;"

# Get current revision from migration files
# Look for: revision = "..."

# Insert correct revision
docker compose exec db-test psql -U fulcrum_test -d fulcrum_test \
  -c "INSERT INTO alembic_version (version_num) VALUES ('<revision_id>');"

# Verify
docker compose exec backend alembic current
```

---

### Issue 3: Multiple Heads

**Symptom**: `alembic upgrade head` fails with "Multiple heads detected".

**Solution:**

```bash
docker compose exec backend alembic merge heads -m "merge heads"
docker compose exec backend alembic upgrade head
```

---

### Issue 4: Column Already Exists

**Symptom**: Migration fails because column already exists.

**Solution**: Check current DB state and manually fix:

```bash
# Check what exists
docker compose exec db psql -U fulcrum -d fulcrum \
  -c "\d table_name"

# If column exists, skip that part of migration or edit migration file
```

---

## Migration File Template

When manually creating/editing migrations:

```python
"""Add entity_names table.

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2026-01-24 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "abc123def456"
down_revision = "previous_revision_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity_names",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_entity_names_id"), "entity_names", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_entity_names_id"), table_name="entity_names")
    op.drop_table("entity_names")
```

---

## Adding Columns to Existing Tables

```python
def upgrade() -> None:
    op.add_column("products", sa.Column("new_field", sa.String(255), nullable=True))

def downgrade() -> None:
    op.drop_column("products", "new_field")
```

**For non-nullable columns with existing data:**

```python
def upgrade() -> None:
    # Add as nullable first
    op.add_column("products", sa.Column("new_field", sa.String(255), nullable=True))
    # Set default value for existing rows
    op.execute("UPDATE products SET new_field = 'default_value' WHERE new_field IS NULL")
    # Make non-nullable
    op.alter_column("products", "new_field", nullable=False)
```

---

## Pre-Migration Checklist

- [ ] Model changes complete
- [ ] Model registered in `__init__.py`
- [ ] Existing tests pass before migration
- [ ] Backup taken (if production)

## Post-Migration Checklist

- [ ] Migration applies cleanly: `alembic upgrade head`
- [ ] Downgrade works: `alembic downgrade -1` then `alembic upgrade head`
- [ ] All tests pass
- [ ] Migration file committed
