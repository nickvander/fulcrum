# Missing Items Tracker

_All onboarding / launch-readiness items are now shipped. This file
tracks the next round of polish + greenfield work. Add new items here
when you find them so the next session has a place to start._

## High Priority

_(none active)_

## Medium Priority

- [ ] **Amazon order ingestion worker** — `AmazonConnector.fetch_orders`
      is real (`d669246`) but there is no job that calls it and
      writes to `SalesOrder` / `SalesOrderItem`. ML has the webhook
      path; Amazon needs a polling worker (Celery beat task) that
      runs every N minutes against the credential and upserts new
      orders, using `CreatedAfter = last_polled_at` so each run only
      pulls the delta.
- [ ] **Margin report: historical cost-at-sale** — today the margin
      report uses `Product.cost_price * units_sold` as the cost
      basis, which drifts every time the buyer updates the master
      cost. `SalesOrderItem` would need a `cost_per_unit` column
      captured at order-create time (in the FULCRUM POS path and the
      ML / Amazon ingestion paths). Once that's in place, swap the
      margin SQL to read from the stored value.

## Future / Strategic

- [ ] Mercado Pago Checkout API integration — research in
      `work/future/mercadopago-checkout-research.md`.
- [ ] Rust backend migration first slice — plan in
      `work/future/81-rust-backend-migration-plan.md`.
- [ ] AI content generation (product descriptions, marketing copy) —
      plan in `work/future/ai-content-generation.md`.
- [ ] Phase 8 Advanced Analytics — ETL pipeline, cost engine,
      interactive charts, alerting. Plan in
      `work/future/80-advanced-analytics.md`.

## Done This Past Week

- [x] Customer onboarding checklist + launch readiness report.
- [x] Supplier document import review queue (incl. AI catalog parsing
      with vendor auto-link).
- [x] Marketplace allocation workflow (stock-transfer model + ML Full
      API).
- [x] OAuth token refresh hardening (401-retry + reauth chip on
      stock-transfer sync panel).
- [x] Low-stock dashboard widget + shopping-cart reorder.
- [x] Demo workspace + cleanup guardrail.
- [x] AI catalog import (CSV + PDF + image), gated on configured key.
- [x] Reusable `report_export` module + 7 reports × CSV + PDF.
- [x] Named CSV import templates ("Map & Template" UX).
- [x] Inventory adjustment audit log UI (`/products/audit`).
- [x] All 5 disabled product-form specs unblocked; frontend 450/0
      skipped.
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
