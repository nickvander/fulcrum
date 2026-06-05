# 97: Next-Session Candidates (scoped shortlist)

> **Created 2026-06-04**, after the inventory-operations overhaul (P0–P2)
> cleared. This is a decision-ready menu: pick one tier-A or tier-B item and a
> session can start immediately. Each entry names the value, scope, effort,
> the truth-source doc, and the "why now". Effort: **S** ≈ one focused session,
> **M** ≈ a session or two, **L** ≈ multi-session.
>
> Grounding: `work/redesign/09-inventory-ops-PICKUP.md` §2 (inventory refactors),
> `work/future/96-fp06-cfdi-timbrado.md` (CFDI), `work/future/93` (ML-seller
> backlog), `work/future/81-rust-backend-migration-plan.md`,
> `work/future/ai-content-generation.md`, `work/future/80-advanced-analytics.md`.
> Primary market = Mexico; primary fulfillment = MercadoLibre **Full**.

---

## Recommendation (TL;DR)

1. **Start with B4-prefill (tier A, S)** — tiny, closes a real operator gap, no
   new infra. Good warm-up / cleanup.
2. **Then FP-06 CFDI P2 (tier B, M–L)** if a Facturama sandbox + CSD is
   available — it's the single highest *customer-asked* value for a Mexican ML
   seller (buyers request facturas constantly), and P1 already laid the rails.
3. **P1-10 OnPush (tier A, S)** is the right pick for a session where a browser
   is connected (it needs per-component visual verification, not just tests).

---

## Tier A — finish-what's-started (small, high-confidence)

### A1. B4 replenishment → PO/transfer **prefill** · S · value: MED
The replenishment planner (`/reports/replenishment`) deep-links "Send → transfer
planner" and "Reorder → supplier PO" with `product`/`qty` query params, but the
transfer planner and PO-edit pages **don't consume them** — the operator
re-enters the quantity. Wire the two destination pages to read the params and
prefill. Truth-source: `work/future/93` §B4 "Open (deferred)". Pure frontend;
small, testable.

### A2. P1-10 — OnPush rollout · S · value: LOW–MED (perf/correctness hygiene)
Convert the ~12 still-Default in-scope components to `ChangeDetectionStrategy.
OnPush` (receiving-dialog, purchase-order-list/edit, the 6 transfer components,
both count components, scan-sku-dialog). **Requires a connected browser** — OnPush
staleness bugs don't surface in unit tests, so each component needs a visual
check after conversion. Do one at a time. Truth-source: PICKUP §2 "Mechanical".

### A3. P2-5/P2-8 polish offcuts · S · value: LOW
- Linkify the audit-page **Source chip** itself (today the per-product dialog
  deep-links origins; the audit table only shows the label + `#id`).
- B6 per-listing fee overrides + bulk-apply on the repricing page (`93` §B6).
- B7 product-level SAT key overrides (single default today; `93` §B7).

---

## Tier B — net-new, high customer value

### B1. FP-06 CFDI **P2** — real timbrado + cancellations · M–L · value: HIGH (MX)
The headline Mexican-seller feature. P1 shipped the mock-tested stamping rails
(`cfdi_documents`, `InvoicingProvider` + `FacturamaInvoicingProvider` +
`MockInvoicingProvider`, per-channel invoicing policy, per-order Stamp/Link UI).
**P2 remaining** (from `work/future/96`):
- Live **Facturama sandbox** verification (payload field names unconfirmed) +
  **CSD upload** (the cert/key live only in Fulcrum, never in vendio).
- **Cancellations** + **nota de crédito** + **factura global** job.
- Per-buyer specific-RFC capture (needs `SalesOrder` receiver columns + a
  capture UI on order detail; B7 also lists this).
**Prereq:** a Facturama sandbox account + test CSD. **Why now:** ML buyers
request facturas constantly; export-only + mock-stamp isn't the real thing.

### B2. AI multimodal listings + per-marketplace tone · M · value: MED–HIGH
The description AI exists (`/ai/generate-description`,
`/ai/generate-listing-description`, gated on `AiService.isReady$()`). Extend it
to (a) feed product **images** into the prompt (multi-modal) and (b) tune tone
per marketplace beyond the current static 3-channel map. Truth-source:
`work/future/ai-content-generation.md` + MISSING_ITEMS "Future/Strategic".
Differentiator for the catalog-creation workflow; gating infra already exists.

### B3. ML Product Ads / Billing API — true ad-spend & settled-fee truth · M · value: MED
B2 (settlement promo/ads classification) already stops `ad_spend = 0`, but true
per-campaign ad spend needs the **ML Product Ads API** (`cost` metric) and the
**ML Billing API** for settled-fee truth. Lights up the margin-by-channel
widget's ad segment with real numbers. Truth-source: `work/future/95` +
`80-advanced-analytics.md`. **Prereq:** ML Ads/Billing API scopes.

---

## Tier C — strategic / infra (do when the trigger fires)

### C1. Rust migration **Phase 0** — instrumentation only · S–M · value: LOW (gate)
Add request-timing + query-count + slow-query metrics around `/api/v1/products`
and capture p50/p95/p99 on 1k/10k/100k catalogs. This is the *gate* that decides
"optimized Python is enough" vs. Phase 2. Phase 1 Python perf wins already
shipped. **Verdict in `93`:** Rust ROI ≈ zero for a single-tenant Mexico seller —
do Phase 0 measurement, keep Phases 2–6 parked. Truth-source: `81`.

### C2. B8 — multi-warehouse / real `stock_locations` table · M · value: LOW–MED
Promote `inventory_items.location` from free-string to a real `stock_locations`
table. **Explicitly deferred** until a second internal warehouse exists —
premature for a single Full seller. Truth-source: `93` §B8.

### C3. Inventory-ops large refactors (PICKUP §2) · M each · value: LOW (debt)
- **P2-12** split the 1,444-line `purchase-order-edit.component.ts` (extract
  receiving / invoice-match / AI concerns).
- **P2-10** ledger virtual-scroll + standalone-routes migration (count/audit
  still use legacy NgModule routing; ledger uses plain `mat-table`).
- **P2-6** planner-as-primary (merge the dumb create-transfer dialog into the
  planner; add "send to Full" suggestions). Higher product value than the other
  two — arguably tier B.

---

## Explicitly NOT doing (and why)
- **Mercado Pago checkout / storefront UI** — lives in the separate **vendio**
  project; Fulcrum is not a direct-to-consumer storefront.
- **One-click PO from low-stock** — POs are emitted supplier-side (portal /
  WhatsApp / email), per operator feedback (MISSING_ITEMS Medium Priority).
- **Geographic heatmaps** — ML-Full hides buyer geography; no data primitive.
- **Founder-decision-pending:** blind-count default (hide `Esperado` until
  commit) — ask before building (PICKUP §2 "Founder decision pending").
