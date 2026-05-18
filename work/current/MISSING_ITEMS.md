# Missing Items Tracker

_All onboarding / launch-readiness items are now shipped. This file
tracks the next round of polish + greenfield work. Add new items here
when you find them so the next session has a place to start._

## High Priority

_(none active)_

## Medium Priority

- [ ] **Amazon FBA inbound reconciliation** — same shape as the ML
      Full inbound reconciliation just shipped, but Amazon's inbound
      API is structured differently (per-shipment item events vs. a
      single status poll). Wire
      `AmazonConnector.get_inbound_shipment_status` to reduce those
      events into the same `InboundShipmentReceivedItem` shape the
      reconciliation service already consumes, then add an
      `amazon-inbound-reconcile` beat schedule entry. The service
      layer in `inbound_shipment_reconciliation.py` is intentionally
      marketplace-agnostic — only the bulk runner today filters to
      `dest_location='ml-full'`. Generalize that filter when Amazon
      lands.
- [ ] **ML webhook subscription health check** — the order poller
      now back-fills missed webhooks, but the subscription itself can
      be missing (operator never subscribed, ML expired it). Add a
      startup or hourly check that POSTs to
      `/applications/{app_id}/notifications` to ensure every healthy
      ML credential has an active `orders` topic subscription.
- [ ] **Frontend Mercado Pago checkout flow** — DEFERRED. The MP
      Checkout API is for a future direct-to-consumer storefront,
      which Fulcrum is not today. ML sales already flow through
      `endpoints/webhooks.py::process_mercadolibre_event` + the new
      `poll_mercadolibre_orders` back-fill worker.

## Future / Strategic

- [ ] Rust backend migration — Phase 0 instrumentation
      (request timing + query count + slow-query log around
      `/api/v1/products`). Required gate before committing to
      Phase 2 Rust foundation. Phase 1 (Python perf wins) has
      shipped — see `work/future/81-rust-backend-migration-plan.md`.
- [ ] Payments: refund + cancel actions on the `/payments` admin UI.
      Backend wires `POST /v1/payments/{id}/refunds` on the MP
      connector; frontend exposes a "Refund" button on the detail
      dialog (full + partial amounts) with confirmation + reason.
- [ ] AI content generation (product descriptions, marketing copy) —
      plan in `work/future/ai-content-generation.md`.
- [ ] Phase 8 Advanced Analytics — ETL pipeline, cost engine,
      interactive charts, alerting. Plan in
      `work/future/80-advanced-analytics.md`.

## Done This Past Week

_(Older items are listed under PROGRESS.md's "Most Recent Shipped"
+ "Recent Archive". Keep this section short — only items from
roughly the last 10 days.)_

- [x] **ML order poller + ML Full inbound reconciliation** —
      `poll_mercadolibre_orders` Celery beat (every 15 min) back-
      fills any orders the ML webhook missed. New
      `MercadoLibreConnector.fetch_orders` paginates
      `/orders/search?seller=X&order.date_created.from=...` (50/page,
      capped at 1k rows/run). Uses the existing `last_orders_polled_at`
      cursor on `MarketplaceCredential` — same column the Amazon
      poller uses. Idempotent on the same `(source, external_order_id)`
      key the webhook upserts on, so a poll + webhook race just
      refreshes status and never re-decrements stock. Helpers
      `_ml_order_to_sales_order` + `_find_local_product_id` lifted
      out of `endpoints/webhooks.py` into the new shared service so
      webhook and poller use one implementation; webhooks.py
      re-imports them under the old names for back-compat.
      `reconcile_ml_inbound_shipments` Celery beat (hourly) closes
      the gap where `StockTransfer.ship(push_to_marketplace=True)`
      stored an `external_inbound_id` but nothing polled ML for the
      actual received state. New `InboundShipmentReceivedItem`
      schema on the connector base + tolerant ML parser (accepts
      `received_quantity` / `quantity_received` / plain `quantity`).
      New `services/inbound_shipment_reconciliation.py` credits
      `ml-full` stock for any positive delta vs. local
      `qty_received`, advances status to PARTIALLY_RECEIVED /
      RECEIVED, sets `received_at` on full. Idempotent; caps
      marketplace over-reporting at `qty_shipped`; logs unmapped
      listings instead of crashing. 26 new backend tests (13 poller
      + 13 reconciliation). Backend 532/8, frontend 518/0.
- [x] **Phase 1 of the Rust migration plan — final tranche of
      Python product-listing perf wins.** The list endpoint no
      longer eager-loads `inventory_adjustments`
      (`noload(self.model.inventory_adjustments)` on the list path);
      replaced with a cheap `inventory_adjustment_count` COUNT
      aggregate added to `_hydrate_product_list_metrics` and
      exposed as a new field on the `Product` schema. Frontend
      `product-list.html` gates the "Stock history" menu item on
      the count; the dialog itself lazy-fetches the full product
      via `getProductById` so the adjustment rows are only loaded
      when needed. Hot-path `print()` in the product-create error
      path replaced with module-logger usage. 2 new backend tests
      + 2 new frontend tests; existing query-count ceiling test
      still passes (now ~17 queries, ceiling `<= 20`). Phase 1
      checklist in the Rust migration plan updated with
      checkbox state — only the list-vs-detail DTO split + Phase 0
      latency-measurement remain.
- [x] **Payments admin UI** — list / detail page for the
      `payments` table. New `/payments` route in the sidenav with a
      Material table (id, created_at, status chip, amount, payer
      email, provider id, sales order link, view-detail action),
      server-side status filter (all/pending/approved/rejected/
      refunded/cancelled), `mat-paginator` (25/50/100 page sizes).
      Per-row "View detail" opens a dialog rendering the meta grid
      + collapsible `<details>` JSON blocks for `raw_response` and
      `last_webhook_payload`, plus a red error block when
      `error_message` is set. New backend `GET /api/v1/payments/`
      paginated list endpoint with `status` / `provider` / `skip`
      / `limit` filters returning `{items, total}`. 5 new backend
      tests + 23 new frontend tests (5 service + 10 page + 8
      dialog). en + es-MX i18n parity green. Backend 504/8, frontend
      516/0.
- [x] AmazonAdapter SP-API completion — `sync_inventory` (PATCH with
      required `marketplaceIds`, MFN `fulfillment_availability`,
      propagates 401 for the retry wrapper) and `fetch_orders` (GET
      `/orders/v0/orders` with `MarketplaceIds`+`CreatedAfter`/
      `NextToken` pagination). Shipped in `d669246`.
- [x] Stockout / velocity / margin reports — three new CSV + PDF
      exports on `endpoints/reports.py` sharing one SalesOrderItem
      aggregation pass. Velocity ranks every product by daily sales;
      margin shows revenue/cost/gross/margin%; stockout is
      velocity-based (out / imminent / watch) distinct from threshold-
      based low-stock. 13 backend tests.
- [x] Marketplace channel cards: reauth chip — implementation was
      already shipped in `7b682c0` (chip state + reconnect button on
      the card). Added 13 frontend tests covering state precedence,
      tooltip with/without reason, and DOM rendering of the chip +
      warn-styled Reconnect button.
- [x] Reports UI for velocity / margin / stockout — new
      `analytics-reports-widget` on the dashboard, with a window
      selector (30/60/90/180d) and CSV + PDF buttons per report.
      Backed by `AnalyticsReportsService` and the shared
      `ReportDownloadService`. 14 new frontend tests (6 service + 8
      widget); endpoints verified live via auth+curl (CSVs return
      real data, PDFs start with %PDF-1.4).
- [x] Margin report: historical cost-at-sale — migration
      `5d9f2a3b1c08` adds `sales_order_items.cost_per_unit`. ML
      webhook and Amazon ingestion now snapshot
      `Product.cost_price` at order-create time. Margin SQL uses
      `SUM(quantity * COALESCE(items.cost_per_unit, products.cost_price))`
      so the report stops drifting on new rows while legacy NULL
      rows still render. 5 new backend tests cover the captured
      path, the legacy fallback, the mixed case, and the
      ingestion-time snapshot for orphan items (NULL).
- [x] Frontend alert-rule management UI — new `/alerts` page in the
      sidenav: Material table of rules with per-row Test / Edit /
      Delete + enabled toggle. Create/Edit dialog with type select,
      threshold + window + cooldown + email, threshold hints that
      change per type. Delete uses the shared ConfirmationDialog.
      Test button shows a per-result snackbar (matched + sent /
      matched + not sent / not matched). 16 new frontend tests
      (6 service HTTP + 10 page DOM + CRUD interactions).
      Live-tested all CRUD via curl: list → create x2 → patch
      disable → test (triggered + email sent) → delete x2 → empty.
- [x] Alerting (low margin / sales dips / stockout risk) — Track 3
      Step 6 of `80-advanced-analytics.md`. Per-user `AlertRule` +
      `AlertEvent` schema, three evaluators sharing the same SQL
      helpers as the velocity/margin/stockout reports, email
      notifications via the existing `EmailService` provider
      (console-by-default; SMTP via `EMAIL_PROVIDER=resend` or
      future channels). Hourly Celery beat task
      `evaluate_alerts`. CRUD API at `/api/v1/alerts/rules` with a
      `/test` endpoint that force-notifies for SMTP-wiring
      verification. Per-rule cooldown prevents notification spam.
      23 new backend tests + live smoke test against the dev
      backend (rule fired, email composed with correct subject +
      HTML, cooldown skip respected on the next tick).
- [x] Mercado Pago Checkout API — backend foundation: new
      `MercadoPagoConnector` (services/mercado_pago.py) wraps
      `POST /v1/payments` + `GET /v1/payments/{id}` with stub
      branch for dev (REJECT- token convention for failure
      simulation). New `Payment` model + migration with
      `(provider, external_payment_id)` unique constraint for
      idempotency. `PaymentStatus.from_mercado_pago` collapses MP's
      ~10 statuses to 5 canonical ones. `POST /api/v1/payments/`
      persists pending → calls connector → applies provider result.
      `POST /api/v1/webhooks/mercadopago` verifies HMAC signature
      (manifest = `id:<data.id>;request-id:<x-request-id>;ts:<ts>;`,
      hmac_sha256) and updates the matching Payment by
      external_id. 26 new backend tests (status mapping, stub
      branch, real-HTTP branch, error capture, network resilience,
      signature accept/tamper/replay/missing/skip, endpoint CRUD,
      webhook idempotency, ghost-id handling, non-payment event
      filtering). Live-smoke-tested all paths end-to-end. Frontend
      Secure Fields + admin UI deferred — see Medium Priority.
- [x] Amazon order ingestion worker — Celery beat task
      `poll_amazon_orders` runs every 15 minutes per
      MarketplaceCredential. New `services/amazon_order_ingestion.py`
      delta-polls SP-API since `MarketplaceCredential.last_orders_polled_at`,
      upserts SalesOrder + SalesOrderItem keyed by
      (source=AMAZON, external_order_id), decrements local stock
      on new orders (idempotent — re-polls only refresh status/total).
      New `AmazonConnector.fetch_order_items` for SP-API line items.
      Migration adds `last_orders_polled_at` to
      `marketplace_credentials`. 14 backend tests; smoke-tested
      live on the dev backend (orders_new + orders_updated + the
      per-credential failure-isolation contract all verified).
