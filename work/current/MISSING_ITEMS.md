# Missing Items Tracker

_All onboarding / launch-readiness items are now shipped. This file
tracks the next round of polish + greenfield work. Add new items here
when you find them so the next session has a place to start._

> **Where things stand (2026-06-04):** the ML-seller backlog (B1–B7) is
> shipped, **FP-06 P1** (CFDI live timbrado) is in (mock-tested), and the
> **inventory-operations overhaul (P0–P2)** is cleared — receiving safety,
> in-transit "+N en camino", structured adjustment `source` end-to-end (audit
> Source column/filter + stock-history origin chips), reconciliation variance
> pills, and count save-rollback. See `work/redesign/09-inventory-ops-PICKUP.md`.
> **Curated next-session shortlist: `work/future/97-next-session-candidates.md`.**
> **Research-grounded idea bank (2025–26 trends): `work/future/98-feature-research-2026.md`.**
> Open threads:
> - **Inventory-ops refactors** (each own session): P1-10 OnPush rollout,
>   P2-6 planner-as-primary, P2-10 ledger virtual-scroll, P2-12 split
>   `purchase-order-edit.component.ts`. See PICKUP §2.
> - **FP-06 P2+** — Facturama live-sandbox verification + CSD upload, then
>   cancellations / nota de crédito / factura-global job
>   (`work/future/96-fp06-cfdi-timbrado.md`).
> - **B8** — multi-warehouse stock-locations (deferred).
> - **Off-backlog**: AI multimodal listings (`work/future/ai-content-generation.md`),
>   advanced analytics (`work/future/80-advanced-analytics.md`).
> - **Small deferred follow-ups**: B4 planner→PO/transfer prefill, B6
>   competitor/buy-box signal, B7 per-buyer specific-RFC capture.
> Storefront/checkout lives in the separate **vendio** project, not here.

## High Priority

_(none active)_

<!-- Most recent High-Priority item shipped on 2026-05-19; see
"Done This Past Week" below. -->

### Closed: Platform Improvements Roadmap (#83)

All six "Best Next Improvements" from
`work/archive/83-platform-improvements-roadmap.md` are now shipped:

- ✅ **Marketplace allocation planning** — Allocation planner → one DRAFT
  transfer per destination; only approved transfers sync to a marketplace.
- ✅ **Supplier document review queue** — imported documents route through a
  review queue before stock movement.
- ✅ **Supplier alias learning** — confirmed Alibaba SKU/name → Fulcrum
  product/variant mappings, reused on future parsing, with review/undo.
- ✅ **Inventory-adjustment safety / reversal** — typed `reason_code` +
  `location`; operator adjustments reversible via
  `POST /api/v1/reports/inventory-adjustments/{id}/reverse` (idempotent,
  equal-and-opposite `correction`).
- ✅ **Operational dashboards** — low-stock, dead-stock, stockout-risk, and
  marketplace pipeline-health surfaces.
- ✅ **CSV export reporting** — CSV (+ PDF) exports for velocity / margin /
  stockout / shrinkage / inventory-adjustment reports.

<details>
<summary>Archived (shipped): Refund + cancellation tracking</summary>

- [x] **Refund + cancellation tracking for marketplace orders
      (MercadoLibre + Amazon).** Today, when an ML / Amazon order
      moves from `COMPLETED` to `CANCELLED` or `REFUNDED`:
        - The poller silently overwrites `SalesOrder.status` — no
          history is kept, so we cannot answer "how many orders did
          we refund last week?".
        - The order falls out of `_REALIZED_ORDER_STATUSES` and the
          rollups stop counting it, but its
          `OrderCostBreakdown` row stays in place as if it were
          still revenue.
        - Stock decremented on first ingestion is never
          re-credited (see "Known bug" below).
        - The Amazon settlement worker parses `RefundEventList` but
          only uses it for fee-netting — partial-refund amounts are
          never persisted.

      This slice surfaces refunds + cancellations as first-class
      data the operator can monitor and alert on.

      **Scope:** read-only tracking of refunds/cancellations
      originated on the marketplace side. Operator-initiated
      refunds on a Fulcrum-hosted Mercado Pago storefront stay
      out of scope (that storefront has no production caller yet
      — see PROGRESS.md "no production caller today").

      **Deliverables (in order):**

      1. **Status-transition audit table.** New
         `sales_order_status_events` table + model + migration:
           - `id`, `order_id` (FK), `from_status`, `to_status`,
             `changed_at`, `source_signal` (one of `ml_webhook`,
             `ml_poll`, `amazon_poll`, `manual`).
         Both pollers
         (`services/mercadolibre_order_ingestion.py:192` and
         `services/amazon_order_ingestion.py:210`) and the ML
         webhook (`endpoints/webhooks.py`) write a row whenever
         `existing.status != new.status`. Idempotent — if the most-
         recent event row for this order already matches
         `(from_status, to_status)`, skip the insert.

      2. **Cost-engine "reversed" marker.** New column on
         `order_cost_breakdowns`: `reversed_at: datetime | None`.
         Set automatically (by the same hook that writes the
         status-transition event) when an order leaves
         `_REALIZED_ORDER_STATUSES`. The rollup / by-channel /
         daily aggregators filter on
         `reversed_at IS NULL` so a reversed order disappears from
         current period totals while staying queryable for the
         refunds widget. Mirrors `fees_source` semantics — strictly
         additive, no rebuild required.

      3. **Amazon partial-refund persistence.** Extend the
         settlement-fee ingestion path
         (`services/settlement_fee_ingestion.py`) to also write
         per-refund-event rows into a new
         `amazon_order_refunds` table when
         `RefundEventList[].ShipmentItemList` is non-empty. Keys
         on `(order_id, amazon_refund_id)` for idempotency.
         Captures the partial-refund case where the order's
         top-level `OrderStatus` stays `SHIPPED` but a buyer
         returned one line item.

      4. **Reports endpoint —
         `GET /api/v1/reports/refunds-summary`.** Returns
         per-channel rollup over a window:
           - `refunds_count` (orders that moved into a non-realized
             status during the window)
           - `refunded_amount_mxn` (sum of those orders'
             `revenue_amount_mxn` + Amazon partial-refund rows in
             window)
           - `refund_rate` (refunds / total orders in window)
         Supports the same `window_days` + `start_date` /
         `end_date` params the velocity/margin/stockout endpoints
         do — uses the shared `_resolve_date_window` resolver.

      5. **Dashboard widget — "Refunds (last 30d)".** New widget
         on the analytics grid. Single-pane card showing total
         count + refunded MXN + rate by channel (Amazon vs ML vs
         FULCRUM). Drill-down link to a future
         `/reports/refunds` list view (out of scope for this
         slice — link is a no-op placeholder).

      6. **Alert rule — refund-rate spike.** Extend
         `services/alert_evaluation_service.py` with a new
         `refund_rate_spike` rule type. Triggers when the trailing
         7d refund rate exceeds the rule's
         `threshold_value` (percentage). Reuses the existing
         `AlertRule` schema; no new schema columns. New rule type
         appears in the `/alerts` create dialog's type select.

      **Known bug, in scope:** the cancellation path does NOT
      re-credit stock. When an ML/Amazon order moves to
      `CANCELLED`, the decremented inventory stays decremented.

      Correct semantics (per channel; refunds vs cancellations
      behave differently):

        - Cancel **before ship** (ML `cancelled` from `paid` with
          `shipping.status` ≠ `shipped`; Amazon `Canceled` from
          `Pending`/`Unshipped`) → **re-credit stock**. We held
          inventory; never sent it.
        - Cancel **after ship** (rare; ML `cancelled` with
          `shipping.status=shipped`; Amazon `Canceled` from
          `Shipped`/`PartiallyShipped`) → **don't re-credit**.
          Product is out the door. Becomes a return if the buyer
          ships back, which requires an operator "received return"
          workflow we don't have yet.
        - Refund (money-only — ML `payments[].status=refunded`
          while the order itself stays `paid`; Amazon partial
          refund via `RefundEventList` while `OrderStatus=Shipped`)
          → **don't re-credit**. Product stays with the buyer.
        - Return → re-credit, but marketplaces don't reliably
          report returns. Out of scope for this slice.

      Implementation:

        - New column `SalesOrder.stock_recredited_at: datetime |
          None`. Set when the re-credit fires; non-NULL → never
          re-credit again (idempotency).
        - Helper `_was_ever_shipped(db, order)`: returns True iff
          the status-event audit (Deliverable 1) contains a row
          where `to_status` ∈ {`SHIPPED`, `DELIVERED`}. Single
          query per cancellation, cheap.
        - In the status-transition hook: when transitioning
          `realized → CANCELLED` AND `not _was_ever_shipped(...)`
          AND `order.stock_recredited_at is None`, call
          `inventory_service.adjust_stock(+qty)` for each line
          item, then set `stock_recredited_at = now()`.
        - The audit-first check side-steps the
          "marketplace-payload shipping subobject might be missing"
          problem — our local audit knows what we ever saw on this
          order, regardless of how complete the cancellation
          webhook payload is.

      **Tests:**
        - Backend: status-event idempotency, reversed_at-on-
          transition hook fires from each ingestion path, refunds-
          summary endpoint contract (per-source filter, window/
          date-range params, realized-vs-reversed math), Amazon
          partial-refund row persistence, alert rule evaluator.
          ~25 new tests.
        - Frontend: widget renders three channels with correct
          totals, service spec covers the new endpoint, alert
          dialog spec covers the new rule type's threshold hint.
          ~12 new tests.

      **i18n** — en + es-MX parity. New keys under
      `dashboard.refundsWidget.*` and `alerts.types.refundRate.*`.

      **Out of scope (explicit non-goals):**
        - Operator-initiated refunds against Mercado Pago Checkout
          (storefront-only; no production caller).
        - Stock re-credit on cancellation (correctness bug; needs
          its own slice).
        - Refund-reason classification (returns vs fraud vs
          unhappy-customer). Marketplaces give us a status only,
          not a reason; classifying it adds operator workflow that
          isn't justified yet.

      **Verification surface:** seed an ML order → flip to
      `CANCELLED` via a webhook fixture → status-event row
      written, `OrderCostBreakdown.reversed_at` set, dashboard
      widget shows it, refunds-summary endpoint returns it. Then
      seed an Amazon order + a `RefundEventList` payload → partial-
      refund row persisted, widget total reflects it.

      **Shipped 2026-05-19** — see PROGRESS.md "Most Recent
      Shipped" for the full per-deliverable rundown. Stock-leak
      bug fixed in the same slice (the "Known bug, in scope"
      callout above).

</details>

## Medium Priority

- [ ] **Frontend Mercado Pago checkout flow** — DEFERRED. The MP
      Checkout API is for a future direct-to-consumer storefront,
      which Fulcrum is not today. ML sales already flow through
      `endpoints/webhooks.py::process_mercadolibre_event` + the new
      `poll_mercadolibre_orders` back-fill worker.
- [ ] **Low-stock → one-click PO dialog** — DEFERRED per operator
      feedback (2026-05-27): purchase orders are created on the
      supplier's side (their order portal, WhatsApp, email) — not
      inside Fulcrum. A pre-filled "create PO from low-stock alert"
      dialog in Fulcrum would be solving the wrong problem. The
      low-stock-list dashboard widget + alert types already cover
      the visibility side. Revisit only if a customer asks for
      first-class supplier PO emission from Fulcrum.

## Future / Strategic

- [ ] Rust backend migration — Phase 0 instrumentation
      (request timing + query count + slow-query log around
      `/api/v1/products`). Required gate before committing to
      Phase 2 Rust foundation. Phase 1 (Python perf wins) has
      shipped — see `work/future/81-rust-backend-migration-plan.md`.
- [ ] AI content generation backend + UI hooks **shipped** —
      `/ai/generate-description` + `/ai/generate-listing-description`
      both exist, frontend buttons gate on
      `AiService.isReady$()`. Remaining: extend the description
      AI to incorporate product images (multi-modal prompt) +
      per-marketplace tone tuning beyond the current 3-marketplace
      static map.
- [ ] Phase 8 Advanced Analytics — ad-spend attribution. **Re-scoped +
      partially shipped:** B2 (ML settlement promo/ads classification)
      and the Amazon `ProductAdsPaymentEvent` capture now populate
      `OrderCostBreakdown.ad_spend_amount` from settlement, so it's no
      longer always 0. Remaining: pull true ad spend from the **ML
      Product Ads API** (`cost` metric, per-campaign/day — see `95`) and
      the **ML Billing API** for settled-fee truth; the disconnected
      marketing `Campaign` per-order link + geographic heatmaps stay
      deferred. Plans in `work/future/80-advanced-analytics.md` + `95`.

## Done This Past Week

_(Older items are listed under PROGRESS.md's "Most Recent Shipped"
+ "Recent Archive". Keep this section short — only items from
roughly the last 10 days.)_

- [x] **Inventory-operations overhaul P0–P2 (2026-06-04)** — the receive →
      warehouse → send-to-Full operator loop. Tracked in
      `work/redesign/08-inventory-ops-audit.md` + `09-inventory-ops-PICKUP.md`.
      - **P2-4** product-list in-transit "+N en camino" (`in_transit_qty` on the
        list API + row/card/peek hint).
      - **P1-9 + P2-8** structured adjustment `source`/`source_id` (migration
        `d3f7a1c8e024`) stamped on every write path; stock-history dialog
        multi-origin deep-link chips; audit-page Source column + filter +
        `/sources` endpoint + CSV/PDF Source column.
      - **P2-5** reconciliation `Discrepancia ±N` variance pill (tolerance-gated,
        in-transit-aware).
      - **P2-3** physical-count save rollback + per-row save-state + skeleton.
      Frontend 943 passing; en + es-MX parity; verified live in-browser against
      `scripts/seed_inventory_demo.py`. Remaining refactors (P1-10/P2-6/P2-10/
      P2-12) in PICKUP §2.

- [x] **ML-seller feature arc (2026-05-30)** — backlog + research in
      `work/future/93` + `95`:
      - **B3** ML Full stockout / lost-buy-box risk alert
        (`ml_full_stockout_risk`).
      - **B1** ML reputation monitor (`marketplace_reputation_snapshots`,
        health-page reputation column, `reputation_risk` alert) + a
        rate-units fix (ML returns 0–1 fractions → normalized to %).
      - **B2** MELI promo/ads cost capture into `ad_spend`/`other_cost`.
      - **Amazon** settlement fee-type split (Commission vs FBA→shipping)
        + `ProductAdsPaymentEvent` → ad_spend.
      - **B5** Buyer Q&A: `marketplace_questions` + ML `fetch_questions`,
        the `questions` webhook (real-time) + a 30-min poll, a SLA
        reports endpoint, and a `/reports/qa` inbox page.
      - **Docs**: marketplace API research (`95`), stale-doc sweep,
        test-stack port fix (8300/6380).

- [x] **Physical-count session workflow + shrinkage report +
      returns dashboard widget** — three coupled slices built on the
      reason-code infrastructure.
      Count sessions: new `inventory_count_sessions` +
      `inventory_count_session_items` tables, eight endpoints under
      `/api/v1/inventory-counts`, two pages (`/inventory/count` list
      + `/inventory/count/:id` detail). Commit writes one
      `reason_code='recount'` adjustment per row where counted !=
      expected and skips NULLs/zeros (idempotent). State machine
      `in_progress → committed | cancelled`.
      Shrinkage report: new
      `GET /api/v1/reports/reason-code-summary` rolls up adjustments
      by reason_code with units lost/gained + value_at_cost; CSV +
      PDF exports share `report_export`. NULL legacy rows surface
      as `'none'`. Wired into the dashboard analytics-reports widget
      as a fifth row.
      Returns widget: new `GET /api/v1/reports/returns-summary`
      aggregates `sales_order_returns` rows by source. Frontend
      `ReturnsWidgetComponent` mirrors the refunds widget; dashboard
      now lays refunds + returns side-by-side at desktop widths.
      +33 backend tests + 35 frontend tests. en + es-MX i18n parity.
      Backend 761/8, frontend 703/0.
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
