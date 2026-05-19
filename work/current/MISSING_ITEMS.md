# Missing Items Tracker

_All onboarding / launch-readiness items are now shipped. This file
tracks the next round of polish + greenfield work. Add new items here
when you find them so the next session has a place to start._

## High Priority

_(none active)_

## Medium Priority

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
- [ ] AI content generation backend + UI hooks **shipped** —
      `/ai/generate-description` + `/ai/generate-listing-description`
      both exist, frontend buttons gate on
      `AiService.isReady$()`. Remaining: extend the description
      AI to incorporate product images (multi-modal prompt) +
      per-marketplace tone tuning beyond the current 3-marketplace
      static map.
- [ ] Phase 8 Advanced Analytics — ad-spend attribution from the
      marketing `Campaign` table (currently always 0). Needs a
      per-campaign-per-order link or a last-touch heuristic.
      Geographic heatmaps still deferred — needs new data
      primitives. Plan in `work/future/80-advanced-analytics.md`.

## Done This Past Week

_(Older items are listed under PROGRESS.md's "Most Recent Shipped"
+ "Recent Archive". Keep this section short — only items from
roughly the last 10 days.)_

- [x] **Phase 8 Track 2 dead-stock widget** — closes the last open
      Track-2 KPI widget. New `GET /api/v1/reports/dead-stock`
      surfaces products with on-hand stock but near-zero recent
      velocity. Per-row info covers on-hand qty, units sold in
      window, daily velocity, days_since_last_sale (NULL for
      never-sold), cost_price, and stock_value_at_cost. Ordering:
      never-sold first, then longest-dead, then highest capital-
      at-risk. Bundles excluded. Dashboard widget renders full-
      width below the 2x2 analytics grid with a capital-at-risk
      tag. 15 new backend tests + 10 new frontend tests. en + es-MX
      i18n parity. Backend 632/8, frontend 604/0.
- [x] **Marketplace fee-config UI** — form + recompute-all button
      on the marketplace detail page. New backend endpoints
      `PATCH /api/v1/marketplace/{id}/fee-config` (partial update,
      rejects negatives) + `POST /api/v1/marketplace/{id}/recompute-cost-breakdowns`
      (synchronous, filters by `OrderSource` derived from the
      marketplace name). UI converts the fractional fee_rate into
      a percent for the form, validates non-negative inputs, shows
      the recompute summary inline. 10 new backend tests + 12 new
      frontend tests. en + es-MX i18n parity. Backend 617/8,
      frontend 594/0.
- [x] **Phase 8 Track 2 dashboard widgets** — four new analytics
      widgets consuming the Track 1 cost-rollup endpoints, laid out
      in a 2x2 grid on the main dashboard:
      1. Today's profit ticker (window_days=1 headline, color-coded
         positive/negative).
      2. Sales vs spend SVG line chart (hand-rolled, no chart library
         dependency).
      3. Margin by channel stacked bar (per-channel cost composition,
         loss-overrun segment when total_cost > revenue).
      4. Top movers Material table (top 10 by revenue with
         per-product net margin; server pro-rates order-level fees
         by revenue share).
      Three new backend endpoints (`/cost-rollup/by-channel`,
      `/cost-rollup/daily`, `/top-movers`). 17 new backend tests +
      32 new frontend tests. en + es-MX i18n parity. Backend 607/8,
      frontend 582/0. "Dead stock" + geographic heatmaps deferred —
      both need new data primitives not currently captured. See
      `work/future/80-advanced-analytics.md`.
- [x] **Phase 8 Track 1 scaffolding** — cost engine + ETL pipeline
      for per-order net-margin analytics. New `order_cost_breakdowns`
      table populated inline by every ingestion path
      (`upsert_breakdown_safe` post-order-flush on Amazon poll, ML
      poll, ML webhook); `backfill_order_cost_breakdowns` Celery
      beat (every 10min) catches anything inline missed. Engine
      computes `cogs + fees + shipping + ad_spend + other =
      total_cost → net_profit → net_margin_percent`. Per-marketplace
      fee config: `Marketplace.default_fee_rate` +
      `default_shipping_cost`. `GET /api/v1/reports/cost-rollup`
      returns the aggregate ready for Track 2. Currency wired
      (`SalesOrder.currency` + `exchange_rate_to_mxn` on breakdown)
      but v1-stubbed to MXN/1.0. Migration `4f7a9c1e3b22`. 26 new
      backend tests covering pure-computation edge cases, upsert
      idempotency, ingest hooks, backfill filters, rollup
      aggregation (filter by source + realized-status enforcement
      + blended margin math), and endpoint HTTP contract. Backend
      590/8, frontend 545/0.
- [x] **Marketplace health page auto-refresh** — 45s background
      polling while the page is open. Pauses while a per-row poll
      or reconcile is in flight (so the embedded health-row patch
      isn't clobbered). Background path stays silent — no loading-
      spinner flash, no snackbar on transient hiccup. Timer torn
      down on destroy. 6 new frontend tests (fake-timer cadence +
      busy-guard + teardown). Frontend 545/0.
- [x] **ML webhook subscription health check** — folded into the
      `/marketplaces/health` page rather than ML's
      `/applications/{app_id}/notifications` (which the docs say is a
      one-time developer-panel config, not a per-user API surface).
      New `Webhooks (24h)` column shows the most-recent
      `WebhookEvent.received_at` per marketplace + a 24h count, and
      flags `webhook_likely_disconnected=True` when the credential is
      older than 24h AND no events have arrived in 24h. Catches both
      "subscription never configured" and "subscription died" without
      false-positives on a freshly-connected credential. The signal
      is read-only over the existing `WebhookEvent` table — no new
      schema, no extra API call to ML. Defensive complement to the
      order back-fill poller. 6 new backend tests + 2 new frontend
      tests. Backend 564/8, frontend 539/0.
- [x] **Marketplace pipeline health page** — new `/marketplaces/health`
      surfaces per-credential auth + order-poll-cursor + open-inbound
      rollups for the three automatic pipelines shipped over the last
      few sessions. Each row has "Poll orders" + "Reconcile inbound"
      buttons that run the existing per-credential entrypoints
      synchronously and patch the row in place from the embedded
      refreshed health. Staleness thresholds (30min for order poll,
      90min for inbound reconcile) are surfaced on the page so the
      operator knows when a number is normal vs. concerning. Backend
      reuses the per-credential code path the Celery beats already
      use — no parallel implementation. 13 new backend tests + 14
      new frontend tests. en + es-MX i18n parity. Backend 558/8,
      frontend 537/0.
- [x] **Amazon FBA inbound reconciliation + manual reconcile-now UI**
      — generalized `inbound_shipment_reconciliation` from
      ML-specific to marketplace-agnostic via
      `MARKETPLACE_INBOUND_TARGETS` registry. New
      `AmazonConnector.get_inbound_shipment_status` makes the two
      SP-API calls (shipment doc + paginated `/items`) and emits the
      canonical `InboundShipmentReceivedItem` shape with
      `SellerSKU`. The reconciliation service's two-step resolution
      (`MarketplaceListing.external_listing_id` first, `Product.sku`
      fallback) is what makes the Amazon path work when listings are
      keyed by ASIN. New `amazon-inbound-reconcile` Celery beat (30
      past every hour). New `last_reconciled_at` column on
      `stock_transfers` (migration `9b2d3e7a5f01`) bumped on every
      poll regardless of whether anything changed.
      `POST /api/v1/stock-transfers/{id}/reconcile` endpoint runs the
      same code path on demand, returning the summary + refreshed
      transfer. Stock-transfer detail UI adds a "Reconcile inbound
      now" button + "Last reconciled" timestamp + a result card
      showing items updated / units received / unmapped listings.
      en + es-MX i18n parity green. 18 new backend tests + 5 new
      frontend tests. Backend 545/8, frontend 523/0.
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
