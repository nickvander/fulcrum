# 93: ML-Seller Feature Backlog (Mexico + MercadoLibre Full)

> **Origin:** Roadmap re-evaluation (2026-05-30) after the multi-currency
> + stock-movement-audit arc. Grounded in the actual backend
> (`mercadolibre.py`, `order_cost_engine.py`, `alert_evaluation_service.py`,
> `marketplace_health_service.py`). Primary market = Mexico; primary
> fulfillment = MercadoLibre **Full**; Amazon secondary; eBay planned.

This is the prioritized backlog of net-new features. Items move to
`work/current/` when active and to `work/archive/` when shipped.

> **API reality check:** `work/future/95-marketplace-api-research.md`
> validates the real MercadoLibre + Amazon payload shapes against
> official docs. It corrects B1/B2 field assumptions (ML reputation
> rates are 0–1 fractions; ML ad spend is a separate Product Ads API,
> not order `fee_details`) and scopes follow-ups (ML Billing API,
> Product Ads API, `/seller-promotions`, Amazon fee-type split +
> `ProductAdsPaymentEvent` + `GET_V2_SELLER_PERFORMANCE_REPORT`).

## Build order (committed)

1. **B3 — ML Full stockout / lost-buy-box risk alert** — ✅ **SHIPPED**
   2026-05-30 (commit `da5a9fe`). New `ml_full_stockout_risk` AlertType;
   per-SKU risk = Full on-hand (`location='ml-full'`) + in-transit
   transfers vs ML-channel velocity over a 14-day Full replenishment
   horizon. See `alert_evaluation_service._evaluate_ml_full_stockout_risk`.
2. **B1 — ML reputation / claims / cancellation-rate monitor** — *active,
   see `work/current/`.*
3. **B2 — MELI promotions / Product-Ads cost capture** — *active, see
   `work/current/`.*

---

## B1 — ML reputation / claims / cancellation-rate monitor  · HIGH · M
- **Value:** Surface the seller's ML reputation thermometer (level,
  power-seller status, claims rate, cancellation rate, delayed-handling)
  before MELI throttles or de-ranks the account. The single most
  existential KPI for an ML seller — it gates buy-box + Full eligibility.
- **Scope:** `MercadoLibreConnector.fetch_seller_reputation` (`GET
  /users/{id}` → `seller_reputation`/`metrics`); persist to a new
  `marketplace_reputation_snapshots` table; surface on the
  `/marketplaces/health` page (extend `marketplace_health_service.py`);
  new `reputation_risk` AlertType reading the latest snapshot (evaluators
  get only `(db, rule)`, no marketplace auth context).
- **Prereq gap:** no reputation call in `mercadolibre.py`; no snapshot
  table. **Complexity: M.**

## B2 — MELI promotions / Product-Ads cost capture  · HIGH · M
- **Value:** Capture per-order promotion discounts + advertising fees so
  net margin reflects reality instead of `ad_spend = 0`. ML deals/campaigns
  + Product Ads are the dominant marketing spend for ML sellers and today
  silently inflate reported margin.
- **Scope:** extend the ML settlement parse (`_extract_settlement_from_order`)
  to pull promotion/discount + advertising fee detail; route into
  `OrderCostBreakdown.ad_spend_amount` / `other_cost_amount` via
  `order_cost_engine.apply_settlement_fees`. Re-targets the long-parked
  "ad-spend attribution" item at marketplace-native data instead of the
  disconnected `Campaign` table. The margin-by-channel widget already
  renders an ad-spend segment — it just lights up.
- **Prereq gap:** `ad_spend` hardcoded 0 (`order_cost_engine.py`); ML
  promo/ads fields not parsed. Payload shape is the main unknown — parse
  defensively, default missing fields to 0. **Complexity: M.**

---

## Backlog (not yet scheduled)

### B4 — Lead-time-aware replenishment-to-Full planner · HIGH · M
"Reorder by date X / send N units to Full by date Y" from velocity +
`SupplierProduct.lead_time_days` + Full transfer time. Closes the
two-stage Mexico supply chain (supplier → internal → Full) the allocation
planner only half-covers. New `/reports/replenishment` that pre-fills the
existing allocation planner. All inputs already exist (`reorder_point`,
`reorder_quantity`, `lead_time_days`, velocity aggregator) — no schema.

### B5 — Buyer Q&A / messaging SLA tracking · MED · M–L — ✅ SHIPPED 2026-05-30
`marketplace_questions` table + `MercadoLibreConnector.fetch_questions`
+ `questions_service` (ingest/refresh/poll) + a `poll_mercadolibre_questions`
Celery beat (30 min) + `GET /reports/questions` (per-row SLA:
answered/pending/breached at 24h) + a `/reports/qa` inbox page with SLA
counters, surfaced under the Marketplaces sidenav group. Remaining
(deferred): answer-from-Fulcrum write path + wiring the ML `questions`
webhook topic (poll covers ingestion today); post-sale messages.

### B6 — Pricing / repricing assistant (margin-floor guard) · MED · M
Suggest price changes from a margin floor (real settled fees + COGS) and a
competitor/buy-box signal; push via the existing `sync_price`. Now that
real fees are known, prevents selling below cost. v1 = margin-floor only
(competitor signal is the uncertain part).

### B7 — SAT/CFDI factura hooks (Mexico tax) · MED (niche) · L
Export sales/expense data in a CFDI-ready shape, then optionally integrate
a PAC (Facturama/SW Sapien) to emit facturas. Uniquely Mexican; ML buyers
frequently request a factura. Full CFDI 4.0 timbrado is regulatory-heavy —
start **export-only**, defer timbrado. No CFDI/RFC primitives exist today.

### B8 — Multi-warehouse / real stock-locations table · LOW–MED · M
Promote `inventory_items.location` from free-string to a real
`stock_locations` table. Explicitly deferred until a second internal
warehouse exists; premature for a single Full seller.

---

## Re-evaluation verdicts on the older roadmap (2026-05-30)

- **Closed as shipped** (now marked in `83-platform-improvements-roadmap.md`
  + `MISSING_ITEMS.md`): marketplace allocation planning, supplier document
  review queue, supplier alias learning, inventory-adjustment safety/
  reversal, operational dashboards, CSV export reporting.
- **Ad-spend attribution** → re-scoped as **B2** (marketplace-native, not
  the generic `Campaign` table).
- **AI multimodal listings + per-marketplace tone** → still worth doing
  (Med); gating infra exists.
- **Rust migration** → Phase-0 *instrumentation* only (request timing /
  query counts); Rust ROI ~zero for a single-tenant Mexico seller. Keep
  Phases 2–6 parked.
- **Geographic heatmaps / Mercado Pago checkout / one-click PO / reorder
  cart** → keep deferred (ML-Full hides buyer geography; POs are emitted
  supplier-side; no storefront).
