# Database Migrations with Alembic

The project uses [Alembic](https://alembic.sqlalchemy.org/) to manage database
schema migrations. This allows us to make changes to our SQLAlchemy models and
apply those changes to the database in a structured, version-controlled way.

## Automatic Migrations on Startup

For local development, the backend service is configured to automatically run
database migrations every time it starts up. This is handled by the
`backend/migrate.sh` script, which is set as the `command` for the `backend`
service in `docker-compose.yml`.

This means that you do not need to run migrations manually. Simply start the
backend services, and the database will be brought up-to-date automatically.

## The Migration Workflow

While you don't need to run migrations manually, you still need to generate them
when you make changes to the database models. The workflow is a two-step
process: **generate** and **review**.

### Step 1: Generate a New Migration

After you make a change to a model in the `src/models/` directory (e.g., add a
new column), you need to ask Alembic to automatically generate a migration
script that reflects this change.

- **Command:**

  ```bash
  # From the project root
  docker compose exec backend alembic revision --autogenerate -m "Your descriptive migration message"
  ```

- **What it does:**
  - Alembic connects to the database and inspects the current state of the
    tables.
  - It compares this to the state of your SQLAlchemy models.
  - It generates a new Python file in `backend/alembic/versions/` containing the
    `upgrade()` and `downgrade()` functions needed to apply and revert your
    changes.

### Step 2: Review the Migration

**Important:** Always review the auto-generated migration script to ensure it's
correct before committing it to version control. Once you're satisfied, commit
the new migration file. The next time you or anyone else starts the application,
this new migration will be applied automatically.
