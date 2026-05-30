# 95: Marketplace API research — MercadoLibre + Amazon

> Researched 2026-05-30 (two web-research subagents) to validate the
> payload shapes our B1 (reputation) + B2 (ad/promo cost) features
> inferred defensively, and to scope proactive Amazon integration.
> Every claim below is from official docs; URLs inline. Treat this as
> the source of truth when wiring real marketplace data.

---

## Part 1 — MercadoLibre (site MLM / Mexico)

### A. Seller reputation — `GET /users/me` → `seller_reputation`

Confirmed structure (official AR sellers-reputation doc):
`seller_reputation.{ level_id, power_seller_status, real_level,
transactions{ total, completed, canceled, period, ratings{positive,
neutral, negative} }, metrics{ sales{period, completed}, claims,
cancellations, delayed_handling_time } }`. Each metric (except `sales`)
is `{ period, rate, value, excluded{real_value, real_rate} }`.

**Corrections vs our shipped B1:**
- ⚠️ **`metrics.*.rate` is a FRACTION 0–1, not a percentage.** `real_rate:
  0.0912` means 9.12%. Our alert threshold + health pill + display all
  assumed percent → **bug** (alert never fires, display shows "0.09%").
  **Fix: normalize fraction→percent (×100) at parse time** so the rest
  of the stack (threshold=percent, banding ≥1.5/≥3, `X%` display) is
  correct. `ratings.{positive,…}` are also fractions 0–1.
- ✅ Key is exactly **`delayed_handling_time`** (our guess + fallback was
  right).
- Spelling split to respect: `transactions.canceled` (one l) vs
  `metrics.cancellations` (two l's).
- `metrics` may be **absent** on the lightweight `/users/me` form (and
  `level_id` null for low-history sellers). For guaranteed metrics,
  take `id` from `/users/me` then `GET /users/{id}`. **Fix: two-step
  fetch.**
- `metrics.*.excluded.real_rate` = pre-seller-protection figure (the
  "true" health). Optional future enhancement to surface it.

Sources: developers.mercadolibre.com.ar/en_us/sellers-reputation,
…/vehicles-manage-users, global-selling.mercadolibre.com/devsite/seller-reputation-global-selling

### B. Order fees / settlement

**Corrections vs our shipped B2:**
- ⚠️ **ML order `payments[]` have NO `fee_details` array** — that's a
  *Mercado Pago* `/v1/payments/{id}` field, not the ML Orders payload.
  Our `_extract_settlement_from_order` `fee_details` classifier is
  therefore **dormant on real ML orders** (harmless — the
  `marketplace_fee` fallback below is what actually fires; and the
  classifier still works if we ever integrate MP payments directly,
  whose `fee_details[]` = `{type, amount, fee_payer}` with types
  `mercadopago_fee/application_fee/financing_fee/shipping_fee/coupon_fee/discount_fee`).
- ✅ Commission is **`payments[].marketplace_fee`** (flat number, e.g.
  14.29) and/or **`order_items[].sale_fee`** — this is current, not
  "older/alternate". Our code reads `marketplace_fee`. Consider also
  summing `order_items[].sale_fee`.
- `payments[].shipping_cost` is **buyer-paid** shipping, not the
  seller's cost — don't read `0` as "free for the seller". Seller
  shipping cost is on `/shipments/{id}` + the Billing API.
- **Billing API = settled truth** (distinct from the order payload):
  `GET /billing/integration/monthly/periods?group={ML|MP}` →
  `…/periods/key/{KEY}/summary/details` (`charges[]{label, amount, type,
  groupId}`, `payment_collected{…}`) → `…/documents`. `group=ML`
  (marketplace fees) vs `group=MP` (Mercado Pago fees). This is where
  commission + shipping + ads charges reconcile by type.

Sources: developers.mercadolibre.com.mx/en_us/manage-sales,
…ar/en_us/billing-reports, MP payments-search reference.

### C. Advertising (Product Ads) + promotions — the key unknown, resolved

- **Ad spend is a SEPARATE API; never in the order payload.** Mercado
  Ads / Product Ads (base `api.mercadolibre.com`): resolve advertiser
  via `GET /advertising/advertisers?product_id=PADS` (`Api-Version: 1`),
  then `GET /advertising/advertisers/{id}/product_ads/campaigns` and
  `/items` (`api-version: 2`, params `date_from`/`date_to` ≤90d,
  `metrics_summary=true`, `aggregation_type=DAILY`). **Spend = the
  `cost` metric** (+ `clicks`, `prints`, `acos`, `roas`, `total_amount`,
  …). MX is in scope. Requires the seller to have enabled Mercado Ads.
  Per-order attribution is **not** available (campaign/item/day grain).
- **Seller-funded promotions** live in `/seller-promotions`
  (`?app_version=v2`): `…/users/{user_id}`, `…/items/{item_id}`,
  `…/promotions/{id}/items`. Funding split = `original_price` vs `price`
  apportioned by **`seller_percentage`** vs `meli_percentage` (co-funded:
  `benefits{type:"REBATE", seller_percent}`). `type` ∈ DEAL,
  MARKETPLACE_CAMPAIGN, PRICE_DISCOUNT, LIGHTNING, DOD, VOLUME, … The
  order payload only carries `coupon_amount`/`coupon_id`, not the split.

Sources: developers.mercadolibre.com.ar/en_us/product-ads-us-read,
global-selling…/mercado-ads, …/en_us/manage-promotion, …/cofunded-campaigns.

### D. Other proactive ML surfaces (future roadmap)
- Claims: `GET /post-purchase/v1/claims/{id}` (**old `/v1/claims/`
  deprecated 2024-05-06**).
- Questions: `GET /questions/search?seller={id}`, answer via `POST /answers` (→ B5).
- Full stock: `GET /marketplace/items/{id}` → `inventory_id` →
  `GET /marketplace/inventories/{inventory_id}/stock/fulfillment?seller_id={id}`
  (`available_quantity`, `not_available_detail[]` damaged/lost/…).

---

## Part 2 — Amazon SP-API + Advertising API (Amazon is secondary)

- **(1) Settlement fees — Easy / already ingested.** Finances
  `listFinancialEvents` (per-order: `…/finances/v0/orders/{orderId}/financialEvents`):
  `ShipmentEvent → ShipmentItemList → ItemFeeList[] → FeeComponent{FeeType,
  FeeAmount}`. `FeeType` is an **open enum** (no closed list) — common:
  `Commission`, `RefundCommission`, `FBAPerUnitFulfillmentFee`,
  `FBAWeightBasedFee`, `FixedClosingFee`, `ShippingChargeback`,
  `RestockingFee`, plus `Principal`/`Shipping`/`ShippingTax`. Split by
  type the way we plan to for ML; bucket unknowns gracefully.
- **(2) Ad spend — Easy (aggregate) / Moderate (detail).** SP-API
  Finances includes **`ProductAdsPaymentEventList[] → ProductAdsPaymentEvent`**
  (`postedDate, transactionType, invoiceId, baseValue, taxValue,
  transactionValue`) = the Sponsored-Products billing total, **already
  in the payload we ingest**, no campaign/order breakdown. Per-campaign/
  ASIN detail needs the **separate Amazon Advertising API** (own LWA app
  + `advertising::campaign_management` scope + profile id + async report
  polling; metric = `cost`). **Per-order ad attribution impossible.**
- **(3) Account-health analog to ML reputation — Moderate.** No live
  score endpoint, but the Reports API `GET_V2_SELLER_PERFORMANCE_REPORT`
  (async XML) carries ODR, late-shipment rate, pre-fulfillment
  cancellation rate, A-to-z claims, policy violations. The direct mirror
  of B1, but poll-based XML. (`GET_SELLER_FEEDBACK_DATA` for feedback.)
- **(4) Notifications API (future push):** `ACCOUNT_STATUS_CHANGED`
  (NORMAL/AT_RISK/DEACTIVATED), `ORDER_CHANGE` (replaces deprecated
  `ORDER_STATUS_CHANGE`), `PRICING_HEALTH`, `LISTINGS_ITEM_ISSUES_CHANGE`,
  `REPORT_PROCESSING_FINISHED`.

Sources: github.com/amzn/selling-partner-api-models (financesV0.json),
developer-docs.amazon.com/sp-api/docs/report-type-values-performance,
…/notification-type-values, advertising.amazon.com/API/docs.

---

## Action items (prioritized)

**Immediate correctness fix (do now — applied this slice):**
1. **B1 reputation rate units** — normalize ML `metrics.*.rate`
   fraction→percent (×100) at parse; fetch `/users/{id}` (two-step) so
   `metrics` is reliably present.

**High value, scoped follow-ups:**
2. **ML Billing API for settled fees** — replace order-payload fee
   estimates with `group=ML`/`group=MP` billing `charges[]` (settled
   truth). Lets B2 ad-charge + real commission flow correctly.
3. **ML Product Ads API** — pull `cost` per campaign/day into ad-spend
   analytics (per-campaign, not per-order). Needs advertiser-id
   resolution + the `Api-Version` headers.
4. **Amazon fee-type split + `ProductAdsPaymentEvent`** — both already
   in the Finances payload we ingest; pure parsing, Easy. Splits Amazon
   fees + surfaces aggregate Amazon ad spend.
5. **ML `/seller-promotions` funding split** — compute seller-funded
   discount as `original_price − price × seller_percentage`.

**Moderate, demand-gated:**
6. Amazon `GET_V2_SELLER_PERFORMANCE_REPORT` → account-health metrics
   (the Amazon analog of B1; async XML Reports pipeline).
7. Notifications API push (ML webhooks already partial; Amazon
   `ACCOUNT_STATUS_CHANGED` for suspension early-warning).
8. Full Amazon Advertising API (per-campaign/ASIN) — lowest priority
   given Amazon is secondary; per-order attribution impossible.
