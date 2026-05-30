# Configuration

The backend application is configured using environment variables. For local
development, these variables are managed in a `.env` file located in the
`backend/` directory. This file is ignored by Git, so you must create it by
copying the template:

```bash
cp backend/.env.example backend/.env
```

The following is a reference for all the variables defined in `.env.example`.

## PostgreSQL

These variables configure the connection to the PostgreSQL database. They are
used by both the main application and the `db` service in `docker-compose.yml`.

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
  - **Description:** The full connection string for the database. This is used
    by SQLAlchemy to connect to the database.
  - **Default:** `postgresql://fulcrum:fulcrum@db:5432/fulcrum`

## Redis

- **`REDIS_URL`**
  - **Description:** The connection URL for the Redis server, used as the
    message broker for Celery.
  - **Default:** `redis://redis:6379/0`

## Rate Limiting

- **`RATE_LIMIT_REDIS_URL`**
  - **Description:** Redis URL backing the request rate limiter. When unset,
    the limiter falls back to `REDIS_URL` / in-memory storage.
  - **Default:** _none_ (`None`).

- **`RATE_LIMIT_DEFAULT`**
  - **Description:** The default per-client request rate limit applied across
    the API, in `slowapi` syntax.
  - **Default:** `100/minute`

## PostgreSQL connection (advanced)

- **`POSTGRES_HOST`**
  - **Description:** Hostname of the PostgreSQL server. Inside the Docker
    Compose network this is the `db` service. Used both directly (the
    entrypoint's `pg_isready` readiness check) and to assemble `DATABASE_URL`
    when one isn't provided explicitly.
  - **Default:** `db`

## Application Secrets

- **`SECRET_KEY`**
  - **Description:** A secret key used for signing JWT tokens for user
    authentication. **This must be a long, random string** — `.env.example`
    ships with a real 64-character hex value so a fresh checkout works, but you
    should generate your own for any shared or production deployment. Generate
    one with:
    `python3 -c "import secrets; print(secrets.token_hex(32))"`
  - **Required:** Yes (no default in code — it must be present in `.env`).

- **`ALGORITHM`**
  - **Description:** The JWT signing algorithm used for access tokens.
  - **Default:** `HS256`

- **`ACCESS_TOKEN_EXPIRE_MINUTES`**
  - **Description:** Lifetime of an issued access token, in minutes.
  - **Default:** `11520` (8 days).

## First Superuser

These variables are used by the application on its first startup to create an
initial administrative user.

- **`FIRST_SUPERUSER_EMAIL`**
  - **Description:** The email address for the initial superuser account.
  - **Default:** `admin@example.com`

- **`FIRST_SUPERUSER_PASSWORD`**
  - **Description:** The password for the initial superuser account.
  - **Default:** `SecurePass123!`

## Encryption & Security

- **`MARKETPLACE_ENCRYPTION_KEY`**
  - **Description:** A 32-byte (256-bit) key used for encrypting sensitive data
    like marketplace credentials. Generate with:
    `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
  - **Required:** Yes (in production)

## Amazon SP-API (Marketplace)

These are optional and only required if integrating with Amazon.

- **`AMAZON_CLIENT_ID`**
  - **Description:** LWA Client ID from Amazon Seller Central Developer Console.
  - **Default:** _none_ (`None`).

- **`AMAZON_CLIENT_SECRET`**
  - **Description:** LWA Client Secret.
  - **Default:** _none_ (`None`).

- **`AMAZON_SELLER_ID`**
  - **Description:** The Amazon Seller / Merchant identifier used when calling
    SP-API.
  - **Default:** `TEST_SELLER_ID`

- **`AMAZON_REDIRECT_URI`**
  - **Description:** OAuth redirect URI registered for the SP-API app; Amazon
    sends the authorization code here after consent.
  - **Default:** `http://localhost:4200/marketplaces/amazon/callback`

- **`AMAZON_SANDBOX`**
  - **Description:** When `true`, the connector targets Amazon's SP-API sandbox
    endpoints instead of production.
  - **Default:** `false`

## MercadoLibre (Marketplace)

- **`ML_CLIENT_ID`**
  - **Description:** App ID from MercadoLibre DevCenter.
  - **Default:** _none_ (`None`).

- **`ML_CLIENT_SECRET`**
  - **Description:** Secret Key from MercadoLibre DevCenter.
  - **Default:** _none_ (`None`).

- **`ML_REDIRECT_URI`**
  - **Description:** OAuth redirect URI registered for the MercadoLibre app;
    MercadoLibre sends the authorization code here after consent.
  - **Default:** `http://localhost:4200/marketplaces/mercadolibre/callback`

## Mercado Pago (Checkout)

These configure the Mercado Pago Checkout connector. All default to `None` so a
dev workspace renders without payment credentials (the connector falls back to
its stub branch).

- **`MERCADOPAGO_ACCESS_TOKEN`**
  - **Description:** Server-side secret used to call the Mercado Pago REST API.
  - **Default:** _none_ (`None`).

- **`MERCADOPAGO_PUBLIC_KEY`**
  - **Description:** Frontend SDK key (sent to the browser).
  - **Default:** _none_ (`None`).

- **`MERCADOPAGO_WEBHOOK_SECRET`**
  - **Description:** The `x-signature` HMAC secret generated by the Mercado Pago
    dashboard when webhooks are enabled; every incoming webhook is verified
    against it.
  - **Default:** _none_ (`None`).

- **`MERCADOPAGO_API_BASE_URL`**
  - **Description:** Base URL for the Mercado Pago REST API.
  - **Default:** `https://api.mercadopago.com`

## AI

- **`GEMINI_API_KEY`**
  - **Description:** API key for Google Gemini, used by the AI content-
    generation features (e.g. product/listing description generation). The AI
    buttons in the UI gate on this being configured.
  - **Default:** _none_ (`None`).
