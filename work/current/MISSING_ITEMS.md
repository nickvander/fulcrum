# Missing Items Tracker

_All onboarding / launch-readiness items are now shipped. This file
tracks the next round of polish + greenfield work. Add new items here
when you find them so the next session has a place to start._

## High Priority

_(none active)_

## Medium Priority

- [ ] **Marketplace channel cards: surface needs_reauthorization** —
      today the reauth chip is only on the stock-transfer sync panel;
      the channel-list cards still ignore it. Cred + flag already exist
      from `87-marketplace-oauth-hardening.md`.
- [ ] **Stockout / velocity / margin reports** — `endpoints/reports.py`
      currently only exposes low-stock. The shared `report_export`
      helper makes each new report ~25 lines once the SQL is known.

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
