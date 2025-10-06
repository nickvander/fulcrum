# 3. Database Migrations with Alembic

The project uses [Alembic](https://alembic.sqlalchemy.org/) to manage database schema migrations. This allows us to make changes to our SQLAlchemy models and apply those changes to the database in a structured, version-controlled way.

## The `migrate.sh` Wrapper Script

Due to complexities with environment variables and Docker's execution context, a wrapper script `backend/migrate.sh` was created to provide a simple and reliable interface for running Alembic commands.

**You should always use this script to perform migration tasks.**

The script ensures that:
-   The correct environment variables (specifically the `DATABASE_URL`) are loaded from the `.env` file.
-   The `alembic` command is executed within the correct context inside the `backend` container.

## Migration Workflow

The typical workflow for making a schema change is a two-step process: **generate** and **apply**.

### Step 1: Generate a New Migration

After you make a change to a model in the `src/models/` directory (e.g., add a new column), you need to ask Alembic to automatically generate a migration script that reflects this change.

-   **Command:**
    ```bash
    # From the project root
    docker compose exec backend ./migrate.sh revision --autogenerate -m "Your descriptive migration message"
    ```
-   **What it does:**
    -   Alembic connects to the database and inspects the current state of the tables.
    -   It compares this to the state of your SQLAlchemy models.
    -   It generates a new Python file in `backend/alembic/versions/` containing the `upgrade()` and `downgrade()` functions needed to apply and revert your changes.
-   **Important:** Always review the auto-generated migration script to ensure it's correct before proceeding.

### Step 2: Apply the Migration

Once the migration script has been generated and reviewed, you can apply it to the database.

-   **Command:**
    ```bash
    # From the project root
    docker compose exec backend ./migrate.sh upgrade head
    ```
-   **What it does:**
    -   Alembic checks which migrations have not yet been applied to the database.
    -   It executes the `upgrade()` function in all pending migration scripts in order, bringing the database schema up to date with your models.
