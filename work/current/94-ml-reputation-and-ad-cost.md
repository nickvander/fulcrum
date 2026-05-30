# 94: Active — ML reputation monitor (B1) + MELI ad/promo cost capture (B2)

> Active build, started 2026-05-30. Full backlog + rationale in
> `work/future/93-ml-seller-feature-backlog.md`. B3 (Full stockout alert)
> already shipped (`da5a9fe`). Build order here: **B1 → B2.**
> Move to `work/archive/` when both land.

## B1 — ML reputation / claims / cancellation-rate monitor

**Goal:** monitor the seller's ML reputation (the KPI that gates buy-box
+ Full eligibility) and alert before MELI throttles the account.

- [x] Backend: `MercadoLibreConnector.fetch_seller_reputation()` +
      `parse_seller_reputation()` (defensive). `GET /users/me` →
      `seller_reputation` + `metrics`.
- [x] Model + migration: `marketplace_reputation_snapshots`
      (`d4a8c1f9e562`) — credential/marketplace scope, level,
      power_seller_status, claims/cancellations/delayed rate+value,
      sales_completed, raw JSON, captured_at.
- [x] `reputation_service`: `capture_snapshot`, `latest_for_credential`,
      `latest_for_user`, `refresh_for_credential` (on-demand capture via
      the asyncio bridge, mirrors the health poll/reconcile actions).
- [x] Reputation block in `marketplace_health_service` health row + the
      `POST .../refresh-reputation` endpoint + a reputation column +
      refresh action on the frontend health page (colour-banded pill).
- [x] New `reputation_risk` AlertType + evaluator (worst of claims /
      cancellations / delayed-handling rate >= threshold, reads latest
      snapshot); migration `e6b3d9a8c741`; surfaced in the alert dialog.
- [x] i18n en + es-MX. Tests: 10 backend + 5 frontend. **Shipped.**

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
- 2026-05-30 — **B1 shipped.** Reputation connector + snapshot table +
  reputation_service + health-page reputation column/refresh +
  reputation_risk alert. Backend reputation/alert/health suites green;
  frontend 755 passed. Next: B2.
