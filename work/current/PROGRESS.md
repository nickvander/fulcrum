# Progress Log

**Status:** Marketplace-side refund + cancellation tracking now
first-class. New `sales_order_status_events` audit (every ingestion
path writes transitions), `order_cost_breakdowns.reversed_at` so
rollups stop counting reversed orders silently, `amazon_order_refunds`
captures partial-refund events from SP-API Finances, and the
lifecycle hook re-credits stock on cancel-before-ship transitions
(idempotent via `SalesOrder.stock_recredited_at`). New
`GET /api/v1/reports/refunds-summary` + dashboard widget surface
per-channel refund count / amount / rate. New `refund_rate_spike`
alert type closes the loop.

Settlement-fee ingestion replaces estimated marketplace
fees with real per-order data from ML (`/orders/{id}` payments +
shipping) and Amazon (SP-API Finances financialEvents). New hourly
Celery beat `poll_settlement_fees` + manual operator endpoint
`POST /marketplaces/health/{id}/sync-settlement-fees`. `OrderCostBreakdown`
gains `fees_source` (`estimated` | `settled`) + `fees_synced_at`
so subsequent recomputes preserve real settled values. Marketplace
health page now has a "Settlement (last synced)" column + per-row
"Sync settlement" button.

AI features are now properly gated: new `GET /api/v1/ai/capabilities`
returns the `(ready, enabled, configured, provider)` predicate, all
3 AI endpoints (`/ai/identify-product`, `/ai/generate-description`,
`/ai/generate-listing-description`) refuse with a localized
`apiErrors.ai.disabled` when the workspace hasn't enabled AI + set
an API key, and the frontend hides the corresponding buttons in
`ProductForm`, `ProductScanner`, and `MarketplaceListingDialog` via
a shared `AiService.isReady$()` stream.

Analytics export endpoints (velocity, margin, stockout) now accept
optional `start_date` / `end_date` query params for explicit
calendar-range filtering ("last quarter") in addition to the
legacy `window_days` window. The dashboard's
`AnalyticsReportsWidget` exposes a paired Material datepicker for
each bound.

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

- Refund + cancellation tracking for marketplace orders. Closes
  the "we have no idea how many orders got refunded last week"
  gap and the stock-leak bug discovered during the audit (cancel-
  before-ship was silently leaving inventory decremented).
  - New `sales_order_status_events` audit table — every
    ingestion path (ML webhook, ML poll, Amazon poll) routes
    status updates through `services/order_lifecycle.apply_status_change`,
    which writes a row on every `old != new` transition.
    `from_status` is nullable for the very first event of an
    order. `source_signal` records which path wrote the row so
    "the poll keeps undoing the webhook" type bugs are
    debuggable from the audit alone.
  - New `order_cost_breakdowns.reversed_at` column — set by the
    same hook when the order transitions OUT of the realized
    set, cleared on transitions back INTO it. The cost-engine
    rollup / by-channel / daily / top-movers queries now filter
    on `reversed_at IS NULL` so a cancelled order disappears
    from current-period totals while staying queryable by the
    refunds widget.
  - New `sales_orders.stock_recredited_at` column + cancel-
    before-ship stock re-credit. When the transition is
    `realized → CANCELLED` AND the audit history shows the order
    was never SHIPPED/DELIVERED AND `stock_recredited_at` is
    NULL, the lifecycle hook credits each line item's qty back
    via `inventory_service.adjust_stock(+qty)`. Idempotent:
    re-polling a cancelled order can't double-credit. Cancel-
    after-ship correctly does NOT re-credit (product is out the
    door). Refunds (money-only, order stays realized) don't take
    this path at all.
  - Amazon partial-refund persistence — new `amazon_order_refunds`
    table. `AmazonConnector.fetch_order_refunds` + parser
    `_extract_refunds_from_events` walk the SP-API
    `RefundEventList` payload that the settlement worker already
    pulls for fee-netting, and the settlement worker now upserts
    per-event refund amounts. Unique on
    `(order_id, amazon_refund_id)` so re-polling can't double-
    count. Captures the partial-refund case where the order's
    top-level `OrderStatus` stays `Shipped`.
  - New `GET /api/v1/reports/refunds-summary` endpoint —
    per-channel rollup (`refunds_count`, `refunded_amount_mxn`,
    `realized_orders_count`, `refund_rate_percent`). Reuses
    `_resolve_date_window` for the same `window_days` /
    `start_date` / `end_date` semantics as velocity/margin/
    stockout. Numerator = distinct status transitions out of
    realized + Amazon partial-refund events in window;
    denominator = realized orders created in window. Rate is
    NULL when denominator is zero so an empty channel isn't
    misread as "perfect".
  - New dashboard widget `RefundsWidgetComponent` — full-width
    below the dead-stock row. Hero shows total count + MXN
    refunded + rate (color-coded: green <2%, amber 2-5%, red
    ≥5%). Per-channel breakdown table hidden for channels with
    zero history.
  - New alert type `REFUND_RATE_SPIKE` — evaluator computes
    refunds/realized × 100 over the rule's window; fires when
    rate >= threshold. Plumbed through email subject + body. The
    `/alerts` create dialog picks up the new type automatically
    via the existing `AlertType` enum.
  - Migration `8b3f1d5e6c70` adds the three new tables /
    columns + widens the `ck_alert_rules_type` CHECK constraint.
  - 22 new backend tests (10 lifecycle + 9 refunds-summary + 3
    alert evaluator) + 8 new frontend tests (6 widget + 2 service).
    en + es-MX i18n parity green. Backend 688/8, frontend 626/0.

- Settlement-fee ingestion (Phase 8 Track 1 follow-up): replaces
  estimated `marketplace_fees_amount` + `shipping_cost_amount` on
  `OrderCostBreakdown` rows with real settled data from each
  marketplace's finance API.
  - `MercadoLibreConnector.fetch_order_billing` reads
    `/orders/{order_id}` and parses `payments[].marketplace_fee`
    (legacy) + `payments[].fee_details[]` (newer) with
    refund-status filtering, plus `shipping.shipping_cost` /
    `shipping.cost`.
  - `AmazonConnector.fetch_order_financials` reads SP-API
    `/finances/v0/orders/{orderId}/financialEvents` and sums every
    Commission / FBA / per-order fee across ShipmentEventList +
    RefundEventList; ShippingChargeList nets across both.
  - New `services/settlement_fee_ingestion.py` orchestrates per-
    credential batches (cap 200/tick, 90-day lookback). Pending
    orders with no fee data yet stay in `estimated` state for the
    next tick to retry.
  - New `services/order_cost_engine.apply_settlement_fees` flips
    `fees_source` to `settled` + bumps `fees_synced_at`; future
    cost-engine recomputes preserve those values (a stale
    operator-changed fee rate can't silently revert real settled
    data).
  - New Celery beat `poll_settlement_fees` (hourly at :40) +
    manual `POST /marketplaces/health/{id}/sync-settlement-fees`
    so the operator can backfill on demand.
  - Marketplace-health page surfaces `last_settlement_synced_at`
    as a new column + a per-row "Sync settlement" button (hidden
    for non-supported marketplaces).
  - Migration `7c2e8d4a91f6`: `fees_source`, `fees_synced_at` on
    `order_cost_breakdowns` + `last_settlement_synced_at` on
    `marketplace_credentials`.
  - 24 new backend tests (parser fixtures + cost-engine settled-
    preservation + sync_for_credential loop + health endpoint
    contract) + 4 new frontend tests (settlement column pill
    state + button visibility + service wrapper). en + es-MX i18n
    parity. Backend 666/8, frontend 618/0.

- AI capability gating: all 3 AI endpoints
  (`/ai/identify-product`, `/ai/generate-description`,
  `/ai/generate-listing-description`) now check
  `ADKManager.is_ready()` and refuse with a localized 400
  (`apiErrors.ai.disabled`) when AI is off or no API key is
  configured. New `GET /api/v1/ai/capabilities` exposes the
  predicate as `{ready, enabled, configured, provider}`. Frontend
  `AiService.getCapabilities()` caches the call with `shareReplay`
  + an `invalidateCapabilities()` hook that the AI settings tab
  calls after a save. `ProductForm`, `ProductScanner`, and
  `MarketplaceListingDialog` subscribe to `isReady$()` so AI
  buttons are *hidden* (not just disabled) when the workspace
  can't actually use them.

- Date-range filters on analytics exports: velocity / margin /
  stockout export endpoints (CSV + PDF) now accept optional
  `start_date` / `end_date` query params (ISO 8601 dates). When
  set, they pin an explicit calendar window; otherwise the legacy
  `window_days` fallback wins so existing callers stay green.
  Inverted ranges return a localized 400
  (`apiErrors.reports.invalidDateRange`). The dashboard's
  `AnalyticsReportsWidget` exposes a pair of `mat-datepicker`
  inputs; the window-days selector auto-disables when either
  picker is set + a clear button reverts to legacy mode. The
  report subtitle line (rendered in both CSV header + PDF) shows
  the calendar range when explicit ("2026-01-01 → 2026-03-31")
  vs. the legacy `window 30d`. 5 new backend tests + 5 new
  frontend tests. en + es-MX i18n parity.

- Phase 8 Track 2 dead-stock widget: closes the last open
  Track-2 KPI widget. New `GET /api/v1/reports/dead-stock`
  surfaces products with on-hand inventory but near-zero
  velocity over a configurable window (default 30d) /
  threshold (default 0.1 units/day). Per-row info: on-hand,
  units_sold, daily_velocity, days_since_last_sale (NULL for
  never-sold products), cost_price, and stock_value_at_cost
  (the capital-at-risk dollars frozen in the SKU). Sort
  order: never-sold first (worst kind of frozen capital),
  then by days_since_last_sale desc, then by
  stock_value_at_cost desc as a tie-breaker. Bundles excluded
  (same rule the velocity/margin reports follow). Dashboard
  widget renders the table full-width below the 2x2
  analytics grid with a capital-at-risk tag in the header.
  15 new backend tests + 10 new frontend tests (9 widget + 1
  service). en + es-MX i18n parity green. Backend 632/8,
  frontend 604/0.
- Marketplace fee-config UI: form + recompute-all button on the
  marketplace detail page so operators can set
  `Marketplace.default_fee_rate` + `default_shipping_cost`
  without a DB shell, then click Recompute to refresh existing
  cost breakdowns with the new rates. New backend endpoints
  `PATCH /api/v1/marketplace/{id}/fee-config` (partial update,
  rejects negatives) + `POST /api/v1/marketplace/{id}/recompute-cost-breakdowns`
  (synchronous, filters by `OrderSource` derived from the
  marketplace name). 10 new backend tests + 12 new frontend
  tests. en + es-MX i18n parity. Backend 617/8, frontend 594/0.
- Phase 8 Track 2 dashboard widgets: four new analytics widgets
  consuming the Track 1 cost-rollup endpoints, laid out in a 2x2
  grid on the main dashboard. (1) **Today's profit** ticker —
  single headline using window_days=1, color-coded positive /
  negative / zero. (2) **Sales vs spend** — hand-rolled SVG line
  chart (no chart library dependency) plotting daily revenue +
  total cost over the last 30 days, with a totals strip below.
  (3) **Margin by channel** — horizontal stacked bar per
  marketplace showing COGS / fees / shipping / ad spend / profit
  proportions, with a loss-overrun segment when total cost exceeds
  revenue. (4) **Top movers** — Material table of top 10 products
  by revenue with per-product net margin (server-side pro-rates
  order-level fees by revenue share). Three new backend endpoints
  power these: `/reports/cost-rollup/by-channel`,
  `/reports/cost-rollup/daily`, `/reports/top-movers`. en + es-MX
  i18n parity green. 17 new backend tests + 32 new frontend tests
  (6 service + 7 today-profit + 7 margin + 10 sales-vs-spend + 8
  top-movers). Backend 607/8, frontend 582/0.
- Phase 8 Track 1 scaffolding (cost engine + ETL pipeline): new
  per-order `order_cost_breakdowns` analytics row populated inline
  by every ingestion path (Amazon poll, ML poll, ML webhook) +
  `backfill_order_cost_breakdowns` Celery beat (every 10 min)
  catches anything missed. Engine computes `cogs + fees + shipping
  + ad_spend + other = total_cost`, then `net_profit` and a blended
  `net_margin_percent`. Per-marketplace fee config exposed as
  `Marketplace.default_fee_rate` + `default_shipping_cost`
  (operator-configurable; defaults to 0.0 so v1 matches the
  existing gross-margin report exactly until rates are set). New
  `GET /api/v1/reports/cost-rollup?window_days=N&source=...`
  returns the aggregate ready for Track 2 dashboard widgets.
  Currency wired (`SalesOrder.currency` + breakdown's
  `exchange_rate_to_mxn`) but v1-stubbed to MXN/1.0 — FX path is a
  follow-up. Migration `4f7a9c1e3b22` adds the breakdown table +
  fee columns + currency column. 26 new backend tests (pure
  computation edge cases, upsert idempotency, ingest hooks,
  recompute filters, rollup aggregation + filtering by source +
  realized-status enforcement, endpoint HTTP contract). Backend
  590/8, frontend 545/0.
- Auto-refresh /marketplaces/health every 45s while open. Pauses
  on per-row action in flight to avoid clobbering the embedded
  health patch. Background path is silent (no loading spinner
  flash, no snackbar on transient hiccup). 6 new frontend tests
  including fake-timer cadence + teardown coverage. Frontend 545/0.
- ML webhook subscription health check (folded into the existing
  marketplace health page). New `Webhooks (24h)` column shows the
  most-recent `WebhookEvent.received_at` for each credential's
  marketplace plus a 24h count, and flags
  `webhook_likely_disconnected=True` when the credential has been
  connected longer than 24h AND no events have arrived in 24h.
  Catches both "subscription never configured" and "subscription
  died" failure modes without false-positives on a freshly-connected
  credential (the two-part age + freshness guard is the key). The
  signal is read-only over the existing `WebhookEvent` table — no
  new schema, no extra API call to the marketplace. Defensive
  complement to the order back-fill poller (which still catches
  missed deliveries automatically); the column tells the operator
  the push channel itself is broken even though no orders are
  silently lost. 6 new backend tests (last-24h window, per-
  marketplace isolation, the disconnect flag's two-part guard, fresh
  credential negative case, shared rollup across credentials for the
  same marketplace) + 2 new frontend tests (classifier + column DOM).
  Backend 564/8, frontend 539/0.
- Marketplace pipeline health page: new `/marketplaces/health`
  surfaces a per-credential rollup of the three automatic pipelines
  (Amazon order poll, ML order poll, ML+Amazon inbound reconciliation).
  Each row shows auth state (with `last_refresh_error` tooltip), the
  most-recent order-poll timestamp with staleness flag at 30min
  (2x the 15min cron), and an inbound rollup counting open transfers
  + how many are stale at 90min (1.5x the hourly reconcile cron).
  Rows sort problems-first: reauth-required, then least-recently-
  polled. Per-row "Poll orders" and "Reconcile inbound" buttons run
  the existing per-credential entrypoints synchronously and patch
  the row in place from the refreshed health payload the action
  endpoints embed. Backend wires `GET /api/v1/marketplaces/health/`,
  `POST /{id}/poll-orders`, `POST /{id}/reconcile-inbound` — all
  reuse the per-credential code path that the Celery beats also use
  (no parallel implementation). 13 new backend tests + 14 new
  frontend tests. en + es-MX i18n parity green. Backend 558/8,
  frontend 537/0.
- Amazon FBA inbound reconciliation + manual reconcile-now UI: the
  reconciliation service is now marketplace-agnostic
  (`MARKETPLACE_INBOUND_TARGETS` registry) so both ML Full and Amazon
  FBA flow through the same code path. New
  `AmazonConnector.get_inbound_shipment_status` makes the two SP-API
  calls (shipment doc + paginated `/items`) and folds the result into
  the canonical `InboundShipmentReceivedItem` shape with `SellerSKU`
  populated in both `external_listing_id` and `sku` so the
  reconciliation service's two-step resolution (`MarketplaceListing`
  first, `Product.sku` fallback) catches Amazon's typical
  ASIN-keyed listing scheme. New `amazon-inbound-reconcile` Celery
  beat (30 past every hour) + new `last_reconciled_at` column on
  `stock_transfers` (migration `9b2d3e7a5f01`) bumped on every poll
  regardless of whether anything changed. New
  `POST /api/v1/stock-transfers/{id}/reconcile` endpoint returns the
  summary + refreshed transfer in one round trip. Stock-transfer
  detail UI gains a "Reconcile inbound now" button and a
  "Last reconciled" timestamp; manual click shows a result card with
  items updated / units received / unmapped listings. en + es-MX
  i18n parity green. 18 new backend tests (9 Amazon-specific + 4
  endpoint + 5 from the bulk-runner refactor) + 5 new frontend tests
  (1 service + 4 detail). Backend 545/8, frontend 523/0.
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
- **Track 2 follow-ups**: only geographic heatmaps remain. Deferred
  — needs shipping-zone or customer-location data not currently
  captured. See `work/future/80-advanced-analytics.md`.
- **Phase 2 of Rust migration** — only after Phase 0 numbers say so.
  Skeleton an Axum `services/catalog-api` crate beside FastAPI.

## Verification Surface

- Backend full suite: `docker compose -f docker-compose.test.yml run --rm
  backend python -m pytest -q --ignore=tests/integration/test_mercadolibre_live.py`
  → 688 passed, 8 skipped at last green.
- Frontend full suite: `npx ng test --watch=false` → 626 passed, 0
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
