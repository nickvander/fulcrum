# Configuration

The backend application is configured using environment variables. For local development, these variables are managed in a `.env` file located in the `backend/` directory. This file is ignored by Git, so you must create it by copying the template:

```bash
cp backend/.env.example backend/.env
```

The following is a reference for all the variables defined in `.env.example`.

## PostgreSQL

These variables configure the connection to the PostgreSQL database. They are used by both the main application and the `db` service in `docker-compose.yml`.

- **`POSTGRES_USER`**
  - **Description:** The username for the PostgreSQL database.
  - **Default:** `fulcrum`

- **`POSTGRES_PASSWORD`**
  - **Description:** The password for the PostgreSQL database.
  - **Default:** `fulcrum`

- **`POSTGRES_DB`**
  - **Description:** The name of the database to use.
  - **Default:** `fulcrum`

- **`DATABASE_URL`**
  - **Description:** The full connection string for the database. This is used by SQLAlchemy to connect to the database.
  - **Default:** `postgresql://fulcrum:fulcrum@db:5432/fulcrum`

## Redis

- **`REDIS_URL`**
  - **Description:** The connection URL for the Redis server, used as the message broker for Celery.
  - **Default:** `redis://redis:6379/0`

## Application Secrets

- **`SECRET_KEY`**
  - **Description:** A secret key used for signing JWT tokens for user authentication. **This must be changed to a long, random string in production.**
  - **Default:** `your_secret_key_here`

## First Superuser

These variables are used by the application on its first startup to create an initial administrative user.

- **`FIRST_SUPERUSER_EMAIL`**
  - **Description:** The email address for the initial superuser account.
  - **Default:** `admin@example.com`

- **`FIRST_SUPERUSER_PASSWORD`**
  - **Description:** The password for the initial superuser account.
  - **Default:** `changeme`
