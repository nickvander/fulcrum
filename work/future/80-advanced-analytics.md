# Phase 8: Advanced Analytics

> **STATUS as of 2026-05-17:** Phase-level roadmap, mostly unimplemented.
> Track 3 Step 5 (Export Service) has its first concrete slice landed —
> CSV export of the low-stock report (`/reports/low-stock/export`).
> See `80-quick-wins-{plan,log}.md` for the export side. All other
> tracks are still open and need design / scoping before implementation.

This phase focuses on transforming the raw data from Fulcrum (Inventory, Orders)
and external Marketplaces (Amazon, MercadoLibre) into actionable business
intelligence.

## 🎯 Objectives

- **Centralized Data**: Create a unified data warehouse (or logical layer) for
  cross-channel analysis.
- **Profitability Visibility**: Real-time calculation of Net Margin at the SKU
  and Order level.
- **Forecasting**: Algorithmic recommendations for purchase orders based on
  sales velocity.

## 📊 Tracks & Steps

### Track 1: Data Aggregation & Normalization

- [~] **Step 1: ETL Pipeline** — scaffolding shipped 2026-05-18.
  - [x] Per-order analytics row (`order_cost_breakdowns`) populated
    inline by the Amazon poll, ML poll, and ML webhook ingestion
    paths via `services/order_cost_engine.upsert_breakdown_safe`.
  - [x] Celery beat backfill (`backfill_order_cost_breakdowns`,
    every 10 min) catches anything ingested before the engine
    landed or anything whose inline upsert failed.
  - [x] `SalesOrder.currency` + `OrderCostBreakdown.exchange_rate_to_mxn`
    wired but v1-stubbed to 1.0 (every order is MXN today). FX-
    aware path is a follow-up.
- [~] **Step 2: Cost Engine** — scaffolding shipped 2026-05-18.
  - [x] `services/order_cost_engine.py` computes `cogs + fees +
    shipping + ad_spend + other = total_cost` per order, then
    `net_profit = revenue - total_cost` and the blended margin %.
  - [x] Per-marketplace fee config: `Marketplace.default_fee_rate`
    + `Marketplace.default_shipping_cost` (operator-configurable;
    defaults to 0.0 so v1 matches the existing gross-margin report
    exactly until rates are set).
  - [x] `GET /api/v1/reports/cost-rollup?window_days=N&source=...`
    returns the aggregate rollup ready for Track 2's dashboard
    widgets.
  - [ ] Per-order settlement fee data from MP / SP-API settlement
    reports (instead of fee-rate estimation). Follow-up.
  - [ ] Ad-spend attribution from the existing marketing `Campaign`
    table. v1 emits 0. Needs a per-campaign-per-order link model
    or a heuristic (last-touch on the channel).

### Track 2: Dashboard Visualization

- [ ] **Step 3: KPI Widgets**
  - "Today's Sales" ticker (aggregated across all channels).
  - "Top Movers" and "Dead Stock" tables.
- [ ] **Step 4: Interactive Charts**
  - Sales vs. Spend over time (Line/Bar charts).
  - Geographic heatmaps of sales.

### Track 3: Reporting Engine

- [~] **Step 5: Export Service** — partial
  - CSV export of the low-stock report landed 2026-05-17. Pattern
    (`StreamingResponse + csv.writer` per report) extends naturally to
    sales-by-channel, inventory health, EOM summaries, etc.
  - PDF generation still open — needs a lib choice.
  - Date-range filtering hooks (per the original objective) not yet
    wired; current low-stock export is "everything in the current
    state of the inventory".
- [ ] **Step 6: Alerting**
  - Notifications for low margin, sudden sales dips, or out-of-stock risks.
