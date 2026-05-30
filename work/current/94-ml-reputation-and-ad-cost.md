# 94: Active — ML reputation monitor (B1) + MELI ad/promo cost capture (B2)

> Active build, started 2026-05-30. Full backlog + rationale in
> `work/future/93-ml-seller-feature-backlog.md`. B3 (Full stockout alert)
> already shipped (`da5a9fe`). Build order here: **B1 → B2.**
> Move to `work/archive/` when both land.

## B1 — ML reputation / claims / cancellation-rate monitor

**Goal:** monitor the seller's ML reputation (the KPI that gates buy-box
+ Full eligibility) and alert before MELI throttles the account.

- [ ] Backend: `MercadoLibreConnector.fetch_seller_reputation()` —
      `GET /users/{id}` → `seller_reputation` (level_id,
      power_seller_status, transactions.ratings) + `metrics`
      (claims / cancellations / delayed_handling rate+value).
- [ ] Model + migration: `marketplace_reputation_snapshots`
      (credential/seller scope, captured_at, level, power_seller_status,
      claims_rate, cancellations_rate, delayed_rate, sales_completed, raw JSON).
- [ ] Persist a snapshot on demand (health refresh) and/or a Celery beat.
- [ ] Surface a reputation block in `marketplace_health_service` + the
      health API + the frontend health page (card + recent-history).
- [ ] New `reputation_risk` AlertType + evaluator reading the latest
      snapshot (threshold = claims-or-cancellation rate %); migration to
      extend the `ck_alert_rules_type` CHECK; surface in the alert dialog.
- [ ] i18n en + es-MX. Tests backend + frontend. Commit + push.

## B2 — MELI promotions / Product-Ads cost capture

**Goal:** stop `ad_spend = 0` from inflating net margin; capture
marketplace-native promo discounts + advertising fees per order.

- [ ] Backend: extend `_extract_settlement_from_order` (ML connector) to
      parse promotion/discount + advertising fee detail (defensive —
      unknown fields default to 0).
- [ ] Route the parsed amounts into `OrderCostBreakdown.ad_spend_amount`
      / `other_cost_amount` via `order_cost_engine.apply_settlement_fees`.
- [ ] Replace the hardcoded `ad_spend = 0.0` path.
- [ ] Tests (parser + cost-engine routing + margin impact). Commit + push.
- [ ] Margin-by-channel widget ad-spend segment lights up (no FE change
      expected — verify).

## Progress log

- 2026-05-30 — Plan filed. B3 shipped earlier today (`da5a9fe`).
  Starting B1.
