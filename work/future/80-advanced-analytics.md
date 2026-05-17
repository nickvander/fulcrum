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

- [ ] **Step 1: ETL Pipeline**
  - Implement background jobs to normalize order data from Amazon/ML into a
    common `AnalyticsOrder` model.
  - Currency conversion handling for international sales.
- [ ] **Step 2: Cost Engine**
  - Breakdown of costs: COGS + Platform Fees + Shipping + Ad Spend = Total Cost.
  - Calculate `NetProfit` per order.

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
