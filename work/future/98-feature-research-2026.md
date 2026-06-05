# 98: Feature Research — Idea Bank (2025–2026 trends)

> **Created 2026-06-04.** A research-grounded menu of net-new feature ideas for
> Fulcrum, filtered for **high value + low bloat + strong fit** to a single
> Mexico MercadoLibre-**Full** seller (Amazon secondary). Sourced from three
> parallel web-research passes (ML/LATAM seller tooling, inventory/ops SaaS,
> AI-in-commerce) cross-referenced against Fulcrum's actual capability map.
>
> **Filtering rule applied:** prefer features that **extend data/flows Fulcrum
> already owns** (lowest bloat, highest fit) over net-new subsystems. Each entry
> notes what it builds on. Companion to `work/future/97-next-session-candidates.md`
> (the immediate inventory-ops-finish shortlist) — this doc is the longer-horizon
> idea bank. Effort: **S** ≈ one session, **M** ≈ a session or two, **L** ≈ multi.

---

## ⭐ Top picks (best value-to-effort, all extend existing features)

1. **Margin-aware "Price to Win" repricer** (extends B6 repricing) · M ·
   *differentiator.* Chase ML's catalog `price_to_win` reference but never drop
   below the SKU's true margin floor (which Fulcrum already computes from settled
   fees + COGS). No generic repricer has the landed-cost picture. Prereq: ML
   `/items/$ID/price_to_win?version=v2` (the old `/products/$ID/items` was shut
   off Oct 2025). [docs](https://developers.mercadolibre.com.mx/en_us/manage-sales/catalog-competition)
2. **Demand forecasting + dynamic safety stock** (upgrades the rule-based
   replenishment planner) · M · *table-stakes.* Replace flat reorder points with
   velocity + seasonality forecasting and variability-based safety stock. This is
   the headline feature of every competitor (Inventory Planner, Cogsy, Netstock)
   and the single biggest gap vs them — and Fulcrum already has the history +
   lead times + planner to plug it into. Stats methods (moving-avg / exp-smoothing
   + seasonal index) capture ~all the ROI; "AI" branding is mostly marketing.
   [Cin7](https://www.cin7.com/blog/inventory-forecasting-software/)
3. **GMROI + cash-tied-up dashboard** (reporting layer over existing COGS/margin)
   · M · *differentiator.* Per-SKU/category GMROI, inventory value over time,
   days-of-inventory, and cash locked in stock. Treats inventory as cash — a
   solo operator's CFO view. Nearly free given the cost engine + dead-stock data
   already exist. [GMROI](https://expandcfo.com/what-is-gmroi/)
4. **Planner → draft-PO one-click** (wires two existing modules) · S ·
   *table-stakes glue.* Turn a replenishment suggestion straight into a draft PO
   (supplier, qty, expected date). Highest value-per-effort on the whole list;
   overlaps the **B4 prefill follow-up** already in doc 97 §A1 — do them together.
5. **AI buyer-message / Q&A drafting, human-in-the-loop** (extends Q&A SLA +
   description AI) · M · *differentiator.* AI drafts replies to ML/Amazon buyer
   questions grounded in *this* seller's order/inventory/policy data; operator
   approves or one-click sends. Highest-frequency repetitive task; grounding on
   own data is the moat a generic chatbot can't match. **Never auto-send refunds**
   — draft→approve only. [QC architecture](https://yuma.ai/blogs/ai-hallucinations-in-customer-service-why-quality-control-architecture-matters)

---

## A. MercadoLibre revenue & visibility (the highest-leverage surface)

- **A1. Catalog buy-box ("competir por catálogo") win/loss monitor** · M ·
  *table-stakes→differentiator.* Poll each listing's catalog status (winning /
  sharing / losing) and *why* (price, installments, shipping, reputation). The
  biggest visibility lever in MX; do it **margin-aware** (tie to Fulcrum COGS).
  Prereq: `price_to_win` v2. [catalog-competition](https://developers.mercadolibre.com.ar/en_us/catalog-competition)
- **A2. Full aged-stock fee forecaster + auto-clearance** (extends transfers/
  inbound recon — Fulcrum already knows received dates) · M · *differentiator.*
  Track each Full SKU's age vs the 5 aging ranges, forecast the "old-stock fee"
  before it hits, and trigger an `UNHEALTHY_STOCK` clearance promo or recommend
  pickup/discard. Recurring margin leakage Fulcrum can pre-empt. [Full costs MX](https://global-selling.mercadolibre.com/learning-center/news/what-are-my-costs-to-operate-with-full-in-mexico)
- **A3. Promotions / deal manager with net-proceeds preview** · M ·
  *table-stakes+overlay.* Discover/opt into ML promo programs (DEAL, LIGHTNING,
  VOLUME, SMART co-funded, SELLER_COUPON, UNHEALTHY_STOCK) and preview **true net
  earnings** before joining. The `/seller-promotions` v2 API now returns a
  `net_proceeds` object — overlay Fulcrum's COGS + Full fee for real margin.
  [manage-promotion](https://developers.mercadolibre.com.ar/en_us/manage-promotion)
- **A4. Product Ads ROAS optimizer** (extends ad-spend/settlement ingestion) ·
  M–L · *differentiator, time-sensitive.* Pull Product Ads metrics and recommend
  bid/budget by lifecycle, with a **margin-true break-even ACOS/ROAS per SKU**
  only Fulcrum can compute. ⏰ ML deprecated `acos_target` → `roas_target`
  (removable **Feb 24 2026**) — migration window now. [new-product-ads](https://global-selling.mercadolibre.com/devsite/new-product-ads)
- **A5. Claims & mediations console** (complements Q&A SLA) · M · *table-stakes
  reputation defense.* Centralize post-sale claims with SLA clocks + buyer/
  mediator messaging + margin-aware resolution (partial vs total refund vs
  return-logistics cost). ⏰ Claims **v1 dead since May 2025** — v2 only.
  [manage-claims](https://global-selling.mercadolibre.com/devsite/manage-claims)
- **A6. Mercado Líder tier "what-if" simulator** (extends existing reputation
  monitor) · S–M · *differentiator.* Simulate how one more claim/cancellation/
  late-ship moves the 60-day ratios and warn **before** a tier downgrade (the
  display already exists; the simulation is the new value). [reputación](https://developers.mercadolibre.com.ar/reputacion-de-vendedores)
- **A7. Settlement-vs-estimate fee reconciliation, incl. Full storage + ads**
  (extends settlement-fee ingestion) · S–M · *table-stakes.* Reconcile actual ML
  billing (Full storage, old-stock, commission, ad spend) against Fulcrum's
  pre-sale estimates per order/SKU; flag variances + catch ML fee errors.
- **A8. Demand & keyword intelligence (Nubimetrics-lite)** · L · *nice-to-have.*
  Most-searched keywords per category + high-demand/low-competition niche flags,
  feeding the PO/replenishment loop. Highest-value but heaviest build (limited
  public keyword data) — park as a later bet. [Nubimetrics](https://www.nubimetrics.com/en/product/mercado)

---

## B. Inventory & cash intelligence (reuses the cost engine)

- **B1. Open-PO liability / cash-commitment timeline** (aggregates existing POs)
  · S–M · *differentiator.* What you owe, when, by supplier, tied to expected
  receipt dates — the "I" in GMROI. Pairs with the GMROI dashboard (top pick #3).
  [Settle](https://www.settle.com/blog/the-12-best-ecommerce-inventory-management-software-solutions-for-2025)
- **B2. Supplier performance scorecards** (derived from PO-promised vs inbound-
  actual, both captured) · M · *differentiator.* On-time %, fill-rate, lead-time
  mean/variance, landed-cost trend per supplier. Lead-time variance feeds the
  safety-stock math (top pick #2). Few SMB tools ship real scorecards; Fulcrum
  has nearly all the source data. [vendor scorecards](https://www.spendflo.com/blog/vendor-scorecard-guide)
- **B3. Anomaly alerts** (extends the alerts engine) · M · *differentiator.*
  Beyond low-stock: sales velocity spike/drop, per-SKU margin erosion, settlement-
  fee creep. With a forecast band (top pick #2) "anomaly = actual outside band."
  The fee-creep alert is especially apt given fee ingestion already exists.
- **B4. Returns / reverse-logistics with auto-disposition** (extends the
  adjustment-`source` machinery — a return is just a new source) · M ·
  *table-stakes for marketplaces.* Grade returns (resell/refurbish/scrap),
  auto-restock saleable units to a location with an audit source + margin-on-
  return. ML return rates are non-trivial. (Note: returns recording already
  exists; this is the *disposition/grading* layer + the new X-API-Key BFF path.)

---

## C. Operator efficiency (cheap, daily-felt, low bloat)

- **C1. Saved report views + scheduled email digests** · S–M · *differentiator
  (cheap).* Save filtered report configs ("low-stock for supplier X") and email
  them daily/weekly. Composition of existing reports + email + scheduler; strong
  retention lever for little code.
- **C2. Bulk operations across SKUs/POs** · S–M · *UX differentiator.* Multi-
  select bulk edits (cost / reorder-point / supplier), bulk-receive PO lines,
  bulk-approve replenishment. Cuts daily operator clicks.
- **C3. Barcode label printing + mobile receive/pick/count UX** · M ·
  *differentiator.* Bulk SKU+barcode label gen + a phone-friendly scan flow for
  receiving/transfers/counts. Multiplies the value of the count + inbound-recon
  features already shipped. (Barcode/QR generation already exists; this is
  print-at-scale + the mobile scan web UI.) [Brightpearl WMS](https://www.brightpearl.com/warehouse-management-system)

---

## D. AI — human-in-the-loop only (finally uses the idle AgentOrchestrator)

> Research consensus: lean into **operator-facing draft→approve**, not customer-
> facing autonomy. Cautionary stats: Gartner — 40% of agentic projects canceled
> by 2027; MIT — 95% of GenAI pilots miss ROI; 2/3 of consumers prefer humans.
> ([Retail Dive](https://www.retaildive.com/news/e-commerce-retailers-investments-agentic-commerce/814833/))

- **D1. AI buyer-message / Q&A drafting** — see top pick #5.
- **D2. Listing-SEO / completeness optimizer (ML + Amazon)** (extends description
  AI) · M · *differentiator.* Score each listing for title-keyword quality +
  attribute completeness + category fit, then draft fixes. Ground on ML's native
  **category/attribute-predictor API** so the AI fills *real* required fields, not
  invented ones. Overlaps "AI multimodal listings" in doc 97. [category-predictor](https://global-selling.mercadolibre.com/devsite/category-predictor)
- **D3. AI alert-triage / ops inbox** (the canonical first job for
  `AgentOrchestrator`) · S–M · *nice-to-have, high leverage.* Cluster + prioritize
  + explain operational alerts and propose the next action. Low bloat, unlocks the
  orchestrator, ties the other features together.
- **D4. AI analytics copilot — "ask your data"** · M–L · *differentiator (lean).*
  NL Q&A over Fulcrum's data with anomaly explanation. Constrain to a curated
  metric set first (read-only, result-grounded) to control cost + hallucination —
  don't build a general BI engine.
- **D5. AI-drafted PO rationale** (extends planner→PO #4 + vendor auto-linking) ·
  M · *nice-to-have.* The forecast/quantities can stay statistical; use the LLM
  only to draft the PO + a written rationale the operator approves.
- **D6. Guardrail + eval + cost-control layer** (foundational, build alongside D1)
  · M (amortized) · *foundational.* Pre/post-LLM validation (groundedness, policy),
  confidence-based escalation, token/spend metering + alerts, eval/regression
  harness. Inaccuracy is the #1 reported GenAI harm (51% of orgs). Pairs with the
  existing prompt-caching discipline.

---

## ⏰ Time-sensitive (ML API deadlines worth acting on)
- **Product Ads `acos_target` → `roas_target`** — deprecated, removable **Feb 24
  2026** (A4).
- **Claims v1 dead since May 2025** — any claims integration must be v2 (A5).
- **Catalog `/products/$ID/items` shut off Oct 2025** — use `price_to_win` v2
  (top pick #1, A1).

> **✅ Verified 2026-06-04 — these are NOT current-code bugs.** A grep of the ML
> connector (`backend/src/services/marketplaces/mercadolibre.py`) confirms Fulcrum
> calls **none** of the three deprecated/dead surfaces today:
> - It does **not** call the catalog `/products/$ID/items` endpoint at all (no
>   buy-box/catalog-competition code exists yet).
> - It does **not** create/edit Product Ads campaigns (so nothing uses
>   `acos_target`) — it only *reads/classifies* ad spend from **settlement** data
>   (`settlement_fee_ingestion.py`, `order_cost_engine.py`).
> - It does **not** use the Claims management API — it only reads the claims
>   *rate* from `/users/{id}` reputation for the `reputation_risk` alert.
>
> The connector's live ML endpoints are `/users/*`, `/items/{id}` +
> `/items/{id}/prices` (current pricing API used by `sync_price`),
> `/sites/*/search`, `/orders/*`, `/shipments`, `/questions` + `/answers` — all
> current. So these deadlines are **forward-looking constraints on the proposed
> A1/A4/A5 features only**; this doc already specifies the correct v2 endpoints.
> No migration/fix is required until/unless those features are built.

---

## 🚫 Explicitly NOT doing (hype / bloat / poor fit)
- **Fully-autonomous customer-facing AI agents** (no human in loop) — concentrates
  the 40%/95% failure risk; keep draft→approve.
- **"Agentic commerce" / AI-shopping-agent storefront optimization** — targets
  *owned storefronts*; Fulcrum is ML-Full-first, storefront lives in **vendio**.
- **Real-time minute-by-minute demand sensing** — needs POS/clickstream volume a
  single seller doesn't generate; daily/weekly forecasting captures the ROI.
- **Batch/lot/expiry + FEFO** — high value *only if* the seller's categories are
  perishable/regulated; otherwise the biggest scope-add here for no benefit.
  Confirm category fit before ever building.
- **Multi-site MX→other ML countries** — MX is primary, expansion is future-only
  (project memory); park.
- **Customer profiles / loyalty / CLV** — wrong product; Fulcrum is seller-ops,
  not CRM.

---

## Suggested sequencing (build order)
1. **Quick wins first** (cheap, reuse existing data): #4 planner→PO, C2 bulk ops,
   C1 saved views/digests, B1 open-PO liability, #3 GMROI/cash dashboard.
2. **Core ML revenue:** #1 margin-aware price-to-win repricer, A1 buy-box monitor,
   A2 Full aged-stock forecaster, A3 promo net-proceeds.
3. **Time-boxed ML API work:** A4 Ads ROAS migration (before Feb 2026), A5 claims v2.
4. **Inventory intelligence:** #2 forecasting + safety stock (one project), B2
   supplier scorecards, B3 anomaly alerts, B4 returns disposition.
5. **AI (with D6 guardrails alongside):** #5 buyer-message drafting, D2 listing-SEO,
   D3 alert triage (unlock the orchestrator), then D4 copilot as appetite allows.
