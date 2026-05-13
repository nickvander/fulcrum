# Progress Log

**Status:** Marketplace allocation workflow + OAuth refresh hardening +
real low-stock dashboard widget all shipped to main.
**Current Phase:** Phase 7 — Customer Onboarding Reliability + Day-to-Day
Operator Tools.

## Current Work

- [88-low-stock-dashboard-widget.md](./88-low-stock-dashboard-widget.md)
- [87-marketplace-oauth-hardening.md](./87-marketplace-oauth-hardening.md)
- [85-customer-onboarding-next.md](./85-customer-onboarding-next.md)

## Important Product Decision

- PO receiving updates Fulcrum internal inventory only. Do not trigger
  MercadoLibre/Amazon stock sync from receiving; marketplace quantities must be
  allocated later in a separate channel-planning workflow.

## Latest Slice

- **Supplier import review filters + bulk reject**:
  `GET /api/v1/purchase-orders/imports/reviews` now accepts comma-separated
  `status` (`approved,rejected` / `all`), `supplier_id`, `created_after/before`,
  `search`, and `limit`. New `POST /imports/reviews/bulk-reject` accepts either
  explicit `review_ids` or a `stale_before` cutoff; non-pending and unknown IDs
  are returned as `skipped_ids` so the UI can show a partial summary instead of
  failing the whole call. UI: **Pending / History / All** filter pills and a
  **Reject stale (>30 days)** button on the supplier import queue. Approved
  review cards link straight to the PO they created; terminal reviews no longer
  open the approve dialog. Verified end-to-end in real Chromium.
- **Low-stock dashboard widget** rebuilt against a real
  `/api/v1/reports/low-stock` endpoint with proper threshold precedence
  (Product.reorder_point > ProductInventorySettings > store default),
  velocity, days-of-inventory, severity chips, and a per-row "Create PO"
  button that prefills the PO form. New `reorder_point` /
  `reorder_quantity` columns on Product. See `88-low-stock-dashboard-widget.md`.
  Verified with mixed-severity seed in real Chromium.
- **Marketplace OAuth refresh hardened**: 5-minute pre-refresh buffer,
  typed `ReauthorizationRequiredError`, `needs_reauthorization` +
  `last_refresh_error` columns on the credential row, and a clear
  reauth banner in the stock-transfer detail page when the credential
  is dead. See `87-marketplace-oauth-hardening.md`. Verified the banner
  in real Chromium.
- **Marketplace allocation workflow (Slices 1-3)**: stock-transfer
  model with explicit DRAFT → SHIPPED → RECEIVED state machine,
  MercadoLibre Full inbound-shipment integration with stub fallback,
  listing-quantity push, allocation planner that bundles draft
  transfers per destination, reconciliation report for shrinkage.
  Archived as `archive/86-marketplace-allocation-workflow.md`.
- **Pre-existing onboarding work** (launch readiness, demo cleanup
  guardrail, import review match assistance) shipped earlier — see
  `85-customer-onboarding-next.md` for the slice that's still in
  flight (visual diff for matched invoice/packing-list docs).

## Next Session Starting Point

- Reorder workflow (shopping-cart style) — pick low-stock products
  across the dashboard, group by supplier, create one draft PO per
  supplier in a single pass.
- Surface `needs_reauthorization` on the marketplace cards / list page
  too (today only the stock-transfer sync panel shows it).
- Wire `force_refresh_access_token()` into a 401-retry decorator on
  connector calls.
- Visual diff for uploaded invoice/packing-list documents that match
  an existing PO (compare extracted vs. PO line items side-by-side,
  surface qty/price deltas).
- Multi-select bulk-reject from the import-review list (checkbox
  column + call `bulk-reject` with `review_ids`) — backend already
  accepts this shape.
- Surface `supplier_id` filter and free-text `search` on the import
  queue UI (backend already supports both).
- Keep the broader future ideas in `work/future/` (marketplace status
  UI sync indicators, advanced analytics, hybrid storefront).

## Recent Archive

- [86-marketplace-allocation-workflow.md](../archive/86-marketplace-allocation-workflow.md) -
  Full marketplace allocation workflow (stock-transfer model, ML Full
  API integration, allocation planner, reconciliation report) plus
  Playwright E2E coverage and docs refresh.
- [84-customer-onboarding-readiness.md](../archive/84-customer-onboarding-readiness.md) -
  Launch readiness report, supplier import review queue, Alibaba sample
  import, and draft PO approval smoke.
- [83-platform-improvements-roadmap.md](../archive/83-platform-improvements-roadmap.md) -
  Supplier alias learning, review/undo, live dummy PO transaction, and
  marketplace allocation guardrails.
- [82-po-receiving-to-inventory-workflow.md](../archive/82-po-receiving-to-inventory-workflow.md) -
  PO document parsing, invoice matching, and exact inventory receiving
  workflow.
- [81-mercadolibre-deep-integration.md](../archive/81-mercadolibre-deep-integration.md) -
  Deep ML Sync & UI Polish.
