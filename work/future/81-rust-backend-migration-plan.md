# Rust Backend Migration Plan

## Goal

Move the performance-sensitive backend surface from Python/FastAPI to Rust while keeping Fulcrum shippable throughout the migration. The first target is product retrieval/listing performance, followed by inventory-heavy workflows and marketplace synchronization. Python should remain available for AI/agent features and any marketplace SDK or integration code that is faster to maintain in Python.

## Current Backend Shape

- API entrypoint: `backend/src/main.py`
- Router composition: `backend/src/api/v1/api.py`
- Product listing endpoint: `backend/src/api/v1/endpoints/products.py`
- Product query layer: `backend/src/crud/crud_product.py`
- Inventory metrics: `backend/src/services/inventory_service.py`
- Marketplace orchestration: `backend/src/services/marketplace_service.py`
- Marketplace listing sync: `backend/src/services/marketplace_listing_service.py`
- Connectors: `backend/src/services/marketplaces/amazon.py`, `backend/src/services/marketplaces/mercadolibre.py`
- Database: SQLAlchemy + PostgreSQL-compatible schema, Alembic migrations, pgvector support.
- Async/background work: Celery + Redis.

## Immediate Performance Findings

Product retrieval is a good first hotspot, but it should be optimized before rewriting. The current product list endpoint:

- Fetches a paginated product page.
- Eager-loads images, marketplace listings, and inventory items.
- Then loops over every product and calls:
  - `calculate_sales_velocity`
  - `calculate_days_of_inventory`, which calls `calculate_sales_velocity` again
  - `get_effective_low_inventory_threshold`
  - `get_effective_low_stock_quantity_threshold`
  - `get_total_stock_quantity`
  - one active campaign count query

For a page of 100 products, that can become hundreds of database queries. Rust will not rescue this if the same query pattern is reproduced. The first milestone should collapse these metrics into set-based SQL and measure the improvement.

Other immediate issues to fix or account for:

- `crud_product.get_multi_paginated` runs a count plus a data query, both against a relationship-heavy query.
- Product search uses `ILIKE '%term%'`, which needs trigram/full-text indexing if search traffic grows.
- Stock filters use subqueries but no obvious composite indexes on `inventory_items.product_id`, `marketplace_listings.product_id`, `marketplace_listings.marketplace_id`, or product search fields beyond basic SQLAlchemy column indexes.
- Marketplace import loops one listing at a time and does per-listing lookup by external listing id and SKU.
- Amazon and MercadoLibre connectors are still partly stubbed, so they are better isolated behind an integration boundary than ported first.

## Migration Strategy

Use a strangler migration, not a rewrite. Keep the existing FastAPI app as the public API initially. Add Rust services behind it, move one bounded capability at a time, and only flip frontend traffic directly to Rust once parity and observability are mature.

Recommended final shape:

- Rust API service for core business APIs:
  - products
  - inventory
  - suppliers and purchase-order read paths
  - marketplace listing records
  - auth-adjacent read/write APIs once stable
- Python services for:
  - marketplace connector adapters where SDK/API churn is high
  - AI/agent features
  - receipt/invoice/product vision workflows
  - compatibility bridge during migration
- Shared PostgreSQL database with one schema owner at a time.
- Async event bus or queue for sync jobs, starting with Redis/Celery compatibility and later moving to a Rust worker stack if needed.

## Rust Stack

Suggested Rust choices:

- Web framework: Axum
- Async runtime: Tokio
- Database: SQLx with compile-time checked queries, or SeaORM if the team strongly prefers ORM ergonomics
- Serialization: Serde
- Validation: validator or garde
- Auth/JWT: jsonwebtoken plus tower middleware
- OpenAPI: utoipa
- Observability: tracing, tracing-subscriber, opentelemetry
- HTTP clients: reqwest
- Background jobs:
  - short term: keep Celery/Python for existing tasks
  - medium term: Rust worker using Redis streams, Faktory, Oban-style table, or a dedicated queue
- Testing:
  - Rust unit/integration tests with testcontainers
  - contract tests against existing FastAPI responses
  - load tests with k6, Locust, or oha

## Phase 0: Baseline And Stabilize

Target duration: 1-2 weeks.

Tasks:

- Add request timing and query count instrumentation around `/api/v1/products`.
- Add endpoint-level latency metrics: p50, p95, p99, error rate, payload size.
- Add database-level visibility: slow query log, `EXPLAIN ANALYZE` snapshots, connection pool stats.
- Seed a realistic catalog: 1k, 10k, and 100k products; multiple images; inventory rows; marketplace listings; campaigns.
- Create contract snapshots for product list/detail responses.

Acceptance criteria:

- We know current p95 latency for product list at 100, 1k, 10k, and 100k products.
- We know query counts for product list and detail.
- We can compare Python and Rust behavior with the same test data.

## Phase 1: Fix Product Listing In Python

Target duration: 1-2 weeks.

This is intentionally before Rust. It separates algorithmic/database bottlenecks from Python runtime overhead.

Tasks:

- [x] Replace per-product metric calls with one aggregate query for
      all visible product ids. Done in commit `114304f` — see
      `_hydrate_product_list_metrics` in
      `backend/src/api/v1/endpoints/products.py`. Covers:
  - [x] total stock by product
  - [x] sales quantity over the last 30 days
  - [x] sales velocity
  - [x] days of inventory
  - [x] active campaign count
  - [x] product-specific inventory thresholds
  - [x] store default thresholds
  - [x] inventory adjustment count (shipped in the Phase-1 follow-up
        commit; eager-loading of the adjustment rows themselves is
        now `noload`-ed on the list path).
- [ ] Avoid `joinedload` explosion on list endpoints; return a
      lightweight list DTO with only fields needed by the product
      table. **Partially done**: `inventory_adjustments` is no longer
      eager-loaded on the list path (replaced with a count aggregate).
      The other heavy relations (`images`, `marketplace_listings`,
      `inventory_items`, `custom_fields`, `variants`, `bundle_components`,
      `part_of_bundles`) are still eager-loaded because the existing
      `ProductList` frontend component reads from them directly. A
      proper list-vs-detail DTO split is deferred — it requires
      frontend changes to trust server-computed `stock_quantity`
      instead of recomputing from `inventory_items`, plus a similar
      lazy-fetch pattern for marketplace status + bundle composition.
- [ ] Add a separate detail endpoint payload for heavy relationships.
      **Deferred**: depends on the DTO split above.
- [x] Add indexes — shipped in migration `8a7c2d4f9b31`:
  - [x] `inventory_items(product_id, location)`
        (`ix_inventory_items_product_id_location`)
  - [x] `sales_order_items(product_id)`
        (`ix_sales_order_items_product_id`)
  - [x] `sales_orders(status, created_at)`
        (`ix_sales_orders_status_created_at`)
  - [x] `marketplace_listings(product_id)`
        (`ix_marketplace_listings_product_id`)
  - [x] `marketplace_listings(marketplace_id, external_listing_id)`
        (`ix_marketplace_listings_marketplace_external`)
  - [ ] optional trigram indexes for product name, sku, description
        search — deferred until search traffic justifies them.
- [x] Remove debug `print` calls in hot paths. Done in the Phase-1
      follow-up commit (`products.py` create-product path now uses
      `logging.getLogger(__name__).warning(...)`).
- [x] Add tests that assert product list query count stays under a
      fixed ceiling — see
      `test_product_list_query_count_stays_bounded` in
      `backend/tests/test_products_api.py`. Current ceiling is
      `<= 20` statements at `limit=100`; the actual path issues ~17
      and is flat with N.

Acceptance criteria:

- [x] Product list query count is stable relative to page size — the
      test asserts the ceiling and would catch a regression.
- [x] Contract tests still match existing frontend expectations —
      `inventory_adjustments` is still present on the list response
      (as `[]`), and the new `inventory_adjustment_count` field is
      additive.
- [ ] Product listing p95 improves materially before any Rust code.
      Measurement still TODO — Phase 0 instrumentation is the
      prerequisite and hasn't been completed yet. Once instrumentation
      lands, capture before/after numbers at 1k / 10k / 100k product
      catalogs and decide whether the optimized Python is sufficient
      or whether Phase 2 (Rust foundation) should proceed.

## Phase 2: Rust Foundation

Target duration: 1-2 weeks.

Tasks:

- Add a `rust/fulcrum-api` or `services/catalog-api` crate.
- Add Axum app skeleton with health, readiness, metrics, tracing, and config.
- Use the existing Postgres database, but keep Alembic as schema owner for now.
- Generate Rust structs that mirror product list/detail API contracts.
- Add Dockerfile and docker-compose service for local dev.
- Add CI tasks for `cargo fmt`, `cargo clippy`, and Rust tests.
- Add a local reverse proxy route so FastAPI can delegate selected endpoints to Rust.

Acceptance criteria:

- Rust service runs locally beside FastAPI.
- Health and metrics endpoints work.
- Rust can read from the existing database.
- CI validates the Rust crate.

## Phase 3: Product Read APIs In Rust

Target duration: 2-4 weeks.

Move read-heavy product endpoints first:

- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `GET /api/v1/products/lookup/barcode`
- optionally semantic/vector search after pgvector support is settled

Implementation notes:

- Use explicit SQL, not ORM relationship loading.
- Build response DTOs from purpose-built queries.
- Keep list payload lightweight.
- Use keyset pagination for large catalogs if frontend UX can support it; otherwise keep offset pagination but document limits.
- Keep FastAPI as the initial public router and proxy/delegate to Rust behind a feature flag.
- Add contract tests that call Python and Rust endpoints against the same fixture database.

Acceptance criteria:

- Rust product list returns API-compatible data.
- Rust p95 is better than optimized Python by a meaningful margin, or the team decides optimized Python is sufficient for that endpoint.
- Rollback is a config flip.

## Phase 4: Product Writes And Inventory

Target duration: 3-5 weeks.

Move write paths only after read paths are stable:

- product create/update/delete
- image metadata operations, but not necessarily file upload storage at first
- stock adjustments
- bundle assembly
- inventory thresholds

Implementation notes:

- Keep barcode/QR image generation in Python initially unless it is a proven bottleneck.
- Use DB transactions for stock adjustment and bundle assembly.
- Add optimistic locking or transaction isolation rules for concurrent stock updates.
- Emit events for marketplace sync instead of calling external APIs inline.

Acceptance criteria:

- Inventory writes are transactionally correct under concurrent load.
- Existing Python tests have Rust equivalents or contract coverage.
- Marketplace sync events are produced reliably.

## Phase 5: Marketplace Boundary

Target duration: 2-4 weeks.

Do not start by rewriting Amazon or MercadoLibre connectors in Rust. Their external APIs, OAuth quirks, sandbox differences, and SDK churn make them good microservice candidates.

Recommended shape:

- Rust owns internal marketplace listing records and sync job scheduling.
- Python owns connector adapters:
  - MercadoLibre OAuth/token refresh/API calls
  - Amazon SP-API signing, feeds/listings, sandbox behavior
  - connector-specific retries and payload translation
- Rust calls Python connector service over HTTP/gRPC or publishes jobs to a queue.
- Connector service returns normalized listing data using the existing `ListingData` concept as the contract.

Tasks:

- Define a marketplace connector protocol:
  - `exchange_code_for_token`
  - `refresh_token`
  - `fetch_all_listings`
  - `publish_listing`
  - `sync_inventory`
  - `sync_price`
  - `get_listing_status`
- Make import listing sync set-based:
  - fetch all external listings
  - load existing marketplace listing ids in one query
  - load matching SKUs in one query
  - bulk insert/update listings
  - bulk create product shells only when explicitly enabled
- Add idempotency keys for publish/import jobs.
- Add retry/backoff and dead-letter handling for external API failures.

Acceptance criteria:

- Marketplace imports no longer do per-listing database lookups.
- Python connector service can be replaced later without changing Rust domain code.
- Failed syncs are observable and retryable.

## Phase 6: More Backend Domains

Target duration: ongoing.

Good Rust candidates:

- suppliers and supplier products
- purchase order read models
- dashboard stats
- audit log reads
- settings reads/writes with low connector coupling

Keep in Python unless there is a strong reason:

- AI endpoints
- ADK agents
- invoice/receipt parsing
- product vision
- marketplace connectors while APIs are still maturing
- scripts and ad hoc maintenance tools

## Data And Schema Ownership

Short term:

- Alembic remains schema owner.
- Rust uses SQLx migrations only for local experiments, if at all.

Medium term:

- Choose one migration system.
- Prefer keeping Alembic until most Python writes are retired, then migrate schema ownership deliberately.

Rules:

- No dual migrations for the same table.
- Add database constraints that both Python and Rust rely on.
- Move JSON string fields to real JSON/JSONB where appropriate before porting logic.

## Performance Targets

Initial targets for product list with realistic data:

- 1k products: p95 under 150 ms server-side
- 10k products: p95 under 250 ms server-side
- 100k products: p95 under 500 ms server-side for indexed filters
- query count for product list: constant, ideally 3-6 queries regardless of page size
- marketplace import: O(number of remote pages + fixed DB batch queries), not O(listings) DB lookups

These should be revised after baseline measurement.

## Deployment And Rollback

- Run FastAPI and Rust side-by-side.
- Route by endpoint and feature flag.
- Start with internal/admin traffic, then all traffic.
- Keep response contract tests in CI.
- Keep a single rollback switch per migrated endpoint.
- Do not remove Python endpoint implementations until Rust has been stable in production-like usage for at least two release cycles.

## Risks

- Rewriting without fixing query shape first gives disappointing Rust results.
- Duplicated business logic can drift between Python and Rust.
- Shared database writes from two services can create consistency bugs.
- Marketplace APIs may dominate latency regardless of language.
- Rust compile-time safety helps correctness, but migration cost is real; use it where it buys latency, concurrency, or reliability.

## Recommended First Work Items

1. Instrument `/api/v1/products` and capture baseline latency/query counts.
2. Rewrite product list metrics into batched aggregate queries in Python.
3. Add missing indexes and run `EXPLAIN ANALYZE`.
4. Create contract tests for product list/detail responses.
5. Scaffold Rust Axum service and implement read-only product list from explicit SQL.
6. Compare optimized Python vs Rust before expanding scope.

