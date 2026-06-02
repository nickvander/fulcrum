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

### B4 — Lead-time-aware replenishment-to-Full planner · HIGH · M — ✅ SHIPPED 2026-06-01
"Reorder by date X / send N units to Full by date Y" from velocity +
`SupplierProduct.lead_time_days` + Full transfer time. Closes the
two-stage Mexico supply chain (supplier → internal → Full) the allocation
planner only half-covers. All inputs already existed (`reorder_quantity`,
`lead_time_days`, ML-scoped velocity) — no schema migration.

Shipped: `services/replenishment_service.build_replenishment_plan` (ML-scoped
velocity + Full on-hand + in-transit, mirroring the `ml_full_stockout_risk`
evaluator) → `GET /reports/replenishment` (+ CSV/PDF export), params
`velocity_window_days` / `full_transfer_lead_days` (14, matches the alert
horizon) / `target_cover_days` / `limit`. Per-SKU severity
(critical/soon/watch) + dated "send to Full by" (capped at internal on-hand)
and "reorder by" actions. Frontend `/reports/replenishment` page under the
"Daily actions" sidenav group; Send → transfer planner, Reorder → supplier
PO (deep-linked with `product`/`qty` query params). es-MX + en localized.
Tests: `backend/tests/test_replenishment_planner.py` (8),
`replenishment-page.component.spec.ts` (6).

**Open (deferred):** the transfer planner / PO flow don't yet *consume* the
`product`/`qty` query params — today the links navigate but the operator
re-enters the quantity. Wiring the prefill is a small follow-up on those two
pages.

### B5 — Buyer Q&A / messaging SLA tracking · MED · M–L — ✅ SHIPPED 2026-05-30
`marketplace_questions` table + `MercadoLibreConnector.fetch_questions`
+ `questions_service` (ingest/refresh/poll) + a `poll_mercadolibre_questions`
Celery beat (30 min) + the ML `questions` webhook topic (real-time
hydration via `GET /questions/{id}?api_version=4`, idempotent on
re-delivery when answered) + `GET /reports/questions` (per-row SLA:
answered/pending/breached at 24h) + a `/reports/qa` inbox page with SLA
counters, surfaced under the Marketplaces sidenav group. Remaining
(deferred): answer-from-Fulcrum write path (`POST /answers`
`{question_id, text}`, ≤2000 chars, `write` scope — see `95`) +
post-sale messages.

### B6 — Pricing / repricing assistant (margin-floor guard) · MED · M — ✅ SHIPPED 2026-06-01
Suggest price changes from a margin floor (real settled fees + COGS) and a
competitor/buy-box signal; push via the existing `sync_price`. Now that
real fees are known, prevents selling below cost. v1 = margin-floor only
(competitor signal is the uncertain part).

Shipped: `services/repricing_service.build_repricing_report` computes, per
`MarketplaceListing`, the price needed to hit a target net margin from COGS +
the SKU's *effective* fee/shipping rate — derived from settled, non-reversed
`OrderCostBreakdown` rows per source (folds in ad + other spend), falling back
to `Marketplace.default_fee_rate`/`default_shipping_cost` when there's no
settled history. `p_floor = (cost + shipping) / (1 - fee_rate - floor)`;
flags `loss` / `below_floor` / `infeasible` (fee+floor ≥ 100%). `apply_price`
pushes an approved price via `call_with_401_retry(connector.sync_price)` and
persists it (sync `asyncio.run` bridge + error-dict + reauth, mirroring
`questions_service.answer_question`). Surfaced as `GET /reports/repricing`
(`margin_floor_percent`, `limit`) + `POST /reports/repricing/apply`
(409 `needs_reauthorization`). Frontend `/reports/repricing` page in the
"Daily actions" sidenav group — per-row Apply with inline Reconnect on reauth.
es-MX + en localized. Tests: `test_repricing_assistant.py` (10) +
`repricing-page.component.spec.ts` (8).

**Open (deferred):** competitor / buy-box signal (the uncertain part);
per-listing fee overrides; bulk-apply.

### B7 — SAT/CFDI factura hooks (Mexico tax) · MED (niche) · L — ✅ SHIPPED (export-only v1) 2026-06-01
Export sales/expense data in a CFDI-ready shape, then optionally integrate
a PAC (Facturama/SW Sapien) to emit facturas. Uniquely Mexican; ML buyers
frequently request a factura. Full CFDI 4.0 timbrado is regulatory-heavy —
start **export-only**, defer timbrado.

Shipped (export-only): `services/cfdi_service` — issuer (emisor) config
stored in `StoreSettings.settings['cfdi']` JSON (no migration; mirrors SMTP)
via `GET`/`POST /settings/cfdi`, and `build_cfdi_report` emitting realized
sales in a CFDI 4.0-ready shape. Every order issued to the RFC genérico
(`XAXX010101000`, "PÚBLICO EN GENERAL") — the factura-global treatment for
consumer marketplace sales. MX prices are IVA-inclusive so IVA is backed out
(`base = amount/(1+iva_rate)`). `GET /reports/cfdi` (JSON) + `/reports/cfdi/export`
(CSV). Frontend `/reports/cfdi` page (date window, totals, issuer-missing
warning → Settings, CSV export) + a Settings → CFDI tab (issuer RFC / razón
social / régimen / CP / default SAT keys / IVA). es-MX + en. Tests:
`test_cfdi_export.py` (9) + `cfdi-page` (7) + `cfdi-tab` (4).

**Open (deferred):** per-buyer **specific-RFC capture** (needs SalesOrder
receiver columns + a capture UI on order detail) — v1 is público-general
only; **PAC timbrado** (Facturama/SW Sapien) to emit signed CFDI XML;
expense-side CFDI (recibidos). No product-level SAT key overrides yet (single
default ClaveProdServ/ClaveUnidad from issuer config).

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
