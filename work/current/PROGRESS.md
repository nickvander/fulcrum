# Progress Log

**Status:** Reports surface complete + surfaced on the dashboard.
AmazonAdapter SP-API surface complete *and* wired to a Celery beat
order-ingestion worker. ML now has a matching delta-poll worker
that back-fills any orders the ML webhook dropped + a Celery beat
job that reconciles ML Full inbound shipments against local
`stock_transfers` rows so warehouse-side receipts flow through to
local stock automatically. Margin report uses historical
cost-at-sale. Alerting ships hourly via Celery beat + email, with
full CRUD UI at `/alerts`. Mercado Pago Checkout backend foundation
(connector, Payment model, create + get endpoints, signed webhook)
shipped along with the operator-facing `/payments` admin UI (parked
for the future-storefront milestone, no production caller today).
Phase 1 of the Rust backend migration plan ("Fix Product Listing In
Python") shipped, only Phase 0 instrumentation + the
list-vs-detail DTO split remain. No active in-flight slice.
**Current Phase:** Phase 7 — Customer Onboarding Reliability + Day-to-Day
Operator Tools.

## Current Work

_(nothing in flight — see `work/future/` for the next strategic
candidates, or pick from "Suggested Next Slices" below.)_

## Important Product Decisions

- PO receiving updates Fulcrum internal inventory only. Do not trigger
  MercadoLibre/Amazon stock sync from receiving; marketplace quantities must
  be allocated later in a separate channel-planning workflow.
- Mexico is the primary market; MercadoLibre Full is the primary fulfillment
  path. FBM / direct storefront are future-only.
- Work happens on `main` directly; scratch `claude/*` branches get rebased
  onto `main`. No PR workflow.

## Most Recent Shipped (last ~10 commits)

- ML order reconciliation polish + ML Full inbound reconciliation:
  two new Celery beat workers + supporting services so the operator
  no longer has to babysit dropped ML webhooks or manually mark
  inbound shipments as received.
  - `poll_mercadolibre_orders` (every 15 min): mirrors the existing
    Amazon order poller. New `MercadoLibreConnector.fetch_orders`
    queries `/orders/search?seller=...&order.date_created.from=...`
    paginated to 50/page, capped at 1k rows/run. New
    `services/mercadolibre_order_ingestion.py` upserts by
    `(source=MERCADOLIBRE, external_order_id)` — the same key the
    webhook uses, so a poll racing the webhook only refreshes
    status/total and never re-decrements stock. Helpers
    `_ml_order_to_sales_order` + `_find_local_product_id` lifted out
    of `endpoints/webhooks.py` into the new shared service module;
    webhooks.py re-imports them under their original private names so
    no external caller breaks. Per-credential SAVEPOINT pattern keeps
    one bad seller from killing the Celery tick. Naturally immune to
    the multi-tenant credential-selection bug that affects the
    webhook path (each credential authenticates with its own token).
  - `reconcile_ml_inbound_shipments` (every hour): closes the gap
    where `StockTransferService.ship(push_to_marketplace=True)`
    stored an `external_inbound_id` but nothing polled ML for the
    actual received state. New `InboundShipmentReceivedItem` schema
    on the connector base + `MercadoLibreConnector._parse_received_items`
    (tolerant of ML's API revisions: accepts `received_quantity`,
    `quantity_received`, plain `quantity`). New
    `services/inbound_shipment_reconciliation.py` iterates open ML
    transfers (SHIPPED / PARTIALLY_RECEIVED with non-NULL
    `external_inbound_id`), maps marketplace receipts back to
    `StockTransferItem` via `marketplace_listings`, credits stock at
    `ml-full` for any positive delta, advances status to
    PARTIALLY_RECEIVED / RECEIVED, sets `received_at` on full.
    Idempotent; caps marketplace over-reports at `qty_shipped`; logs
    unmapped listings instead of crashing.
  - 26 new backend tests (13 order poller + 13 reconciliation).
    Backend 532/8, frontend 518/0.
- Phase 1 of Rust migration — product listing perf tranche:
  `inventory_adjustments` is no longer eager-loaded on the list
  path (`noload` instead of `selectinload`); replaced with an
  `inventory_adjustment_count` aggregate added to
  `_hydrate_product_list_metrics` and exposed on the `Product`
  schema. Frontend `product-list.html` now gates "Stock history"
  on the new count; the dialog itself lazy-fetches the full product
  via `getProductById` so the rows are only loaded when actually
  needed. Hot-path `print()` in product-create error path replaced
  with module-logger. 2 new backend tests
  (`test_product_list_inventory_adjustment_count_reflects_state`,
  `test_product_detail_still_returns_full_inventory_adjustments`)
  + existing query-count ceiling test updated with the new
  expected query budget (~17 queries, ceiling `<= 20`). 2 new
  frontend tests cover the lazy-fetch happy path + the
  error-fallback. Backend 506/8, frontend 518/0.
- Payments admin UI: new `/payments` page in the sidenav under
  Alerts. Material table with status chip, amount/currency, payer
  email, provider id, order link, with a server-side status filter
  (all/pending/approved/rejected/refunded/cancelled) and a paginator
  (25/50/100/page). Per-row "View detail" opens a dialog rendering
  the canonical meta grid + collapsible JSON blocks for
  `raw_response` and `last_webhook_payload`, plus a red error block
  when `error_message` is set. New backend `GET /api/v1/payments/`
  paginated list endpoint with `status` / `provider` / `skip` /
  `limit` filters; `count_payments` returns the pre-pagination
  total so the UI can render `N–M of Total`. 5 new backend tests
  (newest-first ordering, status filter, provider filter, skip+limit
  pagination, auth required) + 23 new frontend tests (5 service + 10
  page + 8 dialog). en + es-MX i18n parity green. Backend 504/8,
  frontend 516/0.
- Mercado Pago Checkout backend foundation: new
  `services/mercado_pago.py` (`MercadoPagoConnector` wrapping
  `POST /v1/payments` + `GET /v1/payments/{id}` + HMAC signature
  verification), `Payment` model + migration (unique on
  provider+external_id for idempotency), `PaymentStatus` enum that
  collapses MP's ~10 statuses to 5, `POST /api/v1/payments/`
  endpoint with pending-row-before-call pattern, signed `POST
  /webhooks/mercadopago`. 26 new backend tests covering every
  layer + live smoke-tested end-to-end. Frontend Secure Fields
  tokenization deferred to a follow-up. Backend 499/8.
- Frontend `/alerts` page: Material table of rules with per-row
  Test / Edit / Delete + enabled toggle. New Add/Edit dialog with
  threshold hints that change per alert type. Delete confirmation
  via the shared ConfirmationDialog. Sidenav entry under
  Operations. en + es-MX i18n. 16 new tests (6 service + 10 page).
  Frontend 493/0.
- Alerting + margin cost-at-sale: per-user `AlertRule`s (low_margin
  / sales_dip / stockout_risk) on the new
  `services/alert_evaluation_service.py`, hourly Celery beat
  `evaluate_alerts`, email via existing EmailService, per-rule
  cooldown, /alerts/rules CRUD API with `/test` for ad-hoc
  evaluation. Migration `5d9f2a3b1c08` adds
  `sales_order_items.cost_per_unit` captured by both ingestion
  paths so the margin report stops drifting when master cost
  changes. 28 new backend tests + live smoke test (rule fired,
  email composed, cooldown respected). Backend 473/8.
- Amazon order ingestion worker: Celery beat task
  `poll_amazon_orders` (every 15 min) polls SP-API per Amazon
  MarketplaceCredential since the per-credential
  `last_orders_polled_at` cursor, upserts `SalesOrder` +
  `SalesOrderItem` rows (source=AMAZON), decrements local stock for
  new orders, advances the cursor on success. New
  `AmazonConnector.fetch_order_items` for SP-API line items.
  Migration `4c8f1d2e9b07` adds the cursor column. New `beat`
  service in docker-compose.yml. 14 backend tests + smoke-tested
  live (orders_new, orders_updated idempotency, per-credential
  failure isolation). Backend 445/8.
- New `analytics-reports-widget` on the dashboard: window selector
  (30/60/90/180d) + CSV/PDF buttons for velocity, margin, and
  stockout. New `AnalyticsReportsService` paired with the shared
  `ReportDownloadService`. Endpoints verified end-to-end via
  auth+curl (200, correct content-type + filename + payload).
  Backend 431/8, frontend 477/0.
- `44722bf` Velocity / margin / stockout reports (CSV + PDF on the
  shared `report_export` module, one shared SalesOrderItem
  aggregation pass) + marketplace channel-list reauth chip coverage
  tests (the chip was already wired up in `7b682c0`; the spec only
  smoke-tested `should create`). Backend 431/8, frontend 463/0.
- `d669246` AmazonConnector SP-API completion: real `sync_inventory`
  (PATCH with required `marketplaceIds`, MFN
  `fulfillment_availability`, propagates 401 so the retry wrapper
  works) and real `fetch_orders` (GET `/orders/v0/orders` with
  `MarketplaceIds`+`CreatedAfter`/`NextToken` pagination, raw-dict
  passthrough). Backend 418/8, frontend 450/0.
- `f8f8b61` Mark product-form specs backlog item done.
- `afb760f` Unblock the 5 skipped product-form specs (frontend 450/0
  skipped, was 432/14 skipped). Root causes were mostly infrastructure
  (TranslocoTestingModule, stale httpMock.expectOne calls, missing mock
  methods, setValue→patchValue); the dead ProductsComponent was deleted.
- `97c5f40` Inventory adjustment audit log UI page (/products/audit) +
  paginated JSON list endpoint.
- `ed546a7` Named CSV import templates ("Map & Template" UX) — model +
  migration, CRUD + preview endpoint, mapping sub-dialog, template
  dropdown on the catalog import dialog.
- `f6cca64` CSV+PDF exports for PO, sales orders, expenses, and the
  inventory adjustment audit log (all on the shared report_export module
  shipped in 1cf3e14).
- `1cf3e14` Reusable report_export module (ReportColumn / ReportTable /
  stream_csv / stream_pdf) + sales-by-channel + inventory-snapshot
  reports. Low-stock refactored onto the same module.
- `cc9b038` AI catalog import (PDF + image), gated on configured API key.
  ADKManager.is_ready() + GET /catalog-imports/capabilities.
- `10e862b` AI vendor auto-link: catalog AI agent extracts the document
  vendor name; endpoint fuzzy-matches to an existing supplier and
  pre-links the review.
- `9dfacd0` Supplier import queue: multi-select bulk-reject + search +
  supplier filter UI.
- `4c7c5b7` Low-stock PDF export (reportlab, severity-colored rows).
- `8fbb37c` AI catalog import: CSV slice (`/api/v1/catalog-imports/...`
  endpoints + dialog).

## Suggested Next Slices

Roughly in order of impact / unblock value:

- **Phase 0 of the Rust migration plan** — instrumentation. Phase 1
  product-listing perf wins have all landed (see Rust plan checkbox
  state); the remaining gate before deciding "optimized Python is
  enough vs. proceed to Rust" is capturing p50/p95/p99 latency on
  realistic 1k / 10k / 100k catalogs. Add request timing + query
  count metrics around `/api/v1/products`.
- **Amazon FBA inbound reconciliation** — same pattern just shipped
  for ML Full. Amazon's inbound API is structured differently
  (per-shipment item events instead of a single status poll), so it
  needs a custom AmazonConnector.get_inbound_shipment_status that
  reduces those events down to the same `InboundShipmentReceivedItem`
  shape the reconciliation service already consumes.
- **ML webhook subscription auto-create** — the order poller now
  back-fills missed webhooks, but a credential's webhook subscription
  itself could go missing (operator never subscribed, or ML expired
  the subscription). Add a startup check that POSTs to ML's
  `/applications/{app_id}/notifications` to ensure every healthy ML
  credential has an active subscription for the `orders` topic.
- **Phase 2 of Rust migration** — only after Phase 0 numbers say so.
  Skeleton an Axum `services/catalog-api` crate beside FastAPI.

## Verification Surface

- Backend full suite: `docker compose -f docker-compose.test.yml run --rm
  backend python -m pytest -q --ignore=tests/integration/test_mercadolibre_live.py`
  → 532 passed, 8 skipped at last green.
- Frontend full suite: `npx ng test --watch=false` → 518 passed, 0
  skipped at last green.
- Pre-commit + pre-push hooks: linter + fast backend tests + i18n parity.

## Recent Archive

- [00-backlog-may-2026.md](../archive/00-backlog-may-2026.md) — Both
  frontend testing items (user-bulk-import + product-form specs)
  shipped.
- [87-sales-orders-cherry-handoff.md](../archive/87-sales-orders-cherry-handoff.md) —
  All 7 commits landed on main.
- [usability-roadmap.md](../archive/usability-roadmap.md) — Items 1–4
  (low-stock dashboard, reorder workflow, marketplace integration,
  supplier catalog import) all shipped. Item 5 (more marketplaces)
  rolls into the standalone Amazon / future-marketplace candidates.
- [ai-invoice-processing.md](../archive/ai-invoice-processing.md) —
  Supplier-document import-review + AI catalog parsing shipped.
- [80-quick-wins-{plan,log}.md](../archive/) — Low Stock Widget,
  Export Service, AI Catalog Import (CSV + PDF), supplier auto-link.
- [86-marketplace-allocation-workflow.md](../archive/86-marketplace-allocation-workflow.md) —
  Stock-transfer model + ML Full API integration + allocation planner.
- [84-customer-onboarding-readiness.md](../archive/84-customer-onboarding-readiness.md) —
  Launch readiness report + supplier import review queue.
