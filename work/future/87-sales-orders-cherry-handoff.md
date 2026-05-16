# 87: Sales Orders Cherry-Pick Landing + Follow-Ups

Handoff after consolidating the marketplace-feedback-loop work from the
abandoned `claude/lucid-shirley-fb162f` branch onto current `origin/main`
(which already contains beautiful-greider's stock-transfer rework).

## Where The Work Lives

Branch: `feature/sales-orders-cherry` (off `origin/main` at `3d904a8`).

Worktree: `/home/nickvander/fulcrum/.claude/worktrees/sales-orders-cherry/`.

Seven commits, all green (277 backend tests pass, frontend production
build clean):

```
f4e73d9 Don't count demo-workspace images as cleanup blockers   (new fix)
e4b2fae Make MercadoLibre sync_inventory/sync_price real, drop dead task   (new)
2a4e0e2 Translate onboarding step + launch readiness section copy via stable keys   (cherry-pick 0e96f25)
d766b9a Translate recently-added UI (marketplaces, allocation, dashboard, orders)   (cherry-pick 55b8c00)
78987e5 Rework PO add/edit + demo catalog with images + product list polish   (cherry-pick 0759c36)
50a118d Make compose ports configurable + harden product.is_bundle   (cherry-pick 740f6e1)
bd1ed36 Add sales orders module and close marketplace feedback loop   (cherry-pick a18def8)
```

To land on main per the project rule of "work on main directly,
claude/* gets rebased onto main", a fast-forward push works because
the branch is a strict descendant of `origin/main`:

```
git push origin feature/sales-orders-cherry:main
```

(Force-push not required.)

## What Was Intentionally Skipped

### Lucid-shirley's `07b0594` ("marketplace allocation workflow + OAuth refresh job")

Dropped entirely. Two reasons:

1. **Allocation is dead.** Beautiful-greider's commits `b4823c8`
   through `1d7d63c` (already on main) replace the allocation concept
   with internal stock transfers. The `marketplace-allocation` Angular
   page was explicitly deleted on main. Resurrecting it would conflict
   architecturally with stock-transfer.
2. **OAuth refresh is already real.** Beautiful-greider's `9541ccb`
   ("Harden marketplace OAuth token refresh") is on main. Lucid-shirley's
   version was less developed.

Net: 100% of `07b0594` is superseded. No salvage value.

## Conflicts Resolved During Cherry-Pick

For traceability when this lands and someone wonders what got merged:

### a18def8 conflicts
- `backend/src/services/marketplaces/mercadolibre.py`: kept beautiful-
  greider's inbound-shipment methods AND a18def8's `fetch_order`.
- `frontend/src/app/dashboard/pages/dashboard/dashboard.component.{ts,html,spec.ts}`:
  kept both `lowStock$`/`LowStockService`/`LowStockListWidget` AND
  `salesSummary$`/`SalesOrdersService`/`SalesByChannelWidget`.

### 740f6e1 conflicts
- `backend/src/models/product.py`: kept the `is_bundle = nullable=False,
  server_default="false"` hardening AND main's `reorder_point`/
  `reorder_quantity` columns.
- Migration `4d2c8a01b9f3_backfill_product_is_bundle.py`: rewrote
  `down_revision` from `3c1b4f9e7a02` (an orphan that only existed on
  lucid-shirley) to `d4e5f6a7b8c9` (the actual head on origin/main).

### 55b8c00 conflicts
- `frontend/src/app/marketplaces/pages/marketplace-allocation/marketplace-allocation.ts`:
  modify/delete conflict (translation tried to update a file deleted on
  main). Deleted version wins — allocation page stays gone.
- `frontend/src/assets/i18n/{en,es-MX}.json`: dropped the entire
  `allocation.*` namespace from 55b8c00 since the allocation UI doesn't
  exist anymore. Kept everything else (channels list, sync messages,
  channel widget, onboarding/launch-readiness keys).

## Bug Found + Fixed During Verification

`f4e73d9`: 0759c36 added a demo-workspace `ProductImage` to the Starter
Widget but didn't update the cleanup guardrail. The guardrail counts
any `ProductImage` row as "customer setup" and blocks cleanup, which
broke two existing tests (`test_demo_data_report_lists_cleanup_records`,
`test_demo_data_cleanup_removes_only_seeded_records`).

Fix: filter `ProductImage` rows by `source = "demo_workspace"` so demo-
seeded images are part of the demo fingerprint, not customer setup.
Same pattern as the existing adjustment exclusion for the demo PO.

This bug also exists on `claude/lucid-shirley-fb162f`. The lucid-shirley
author either didn't run the test or didn't notice.

## Pre-Existing Issues NOT Touched

These were on the original lucid-shirley handoff and remain TODO:

### High-value next slice
1. **End-to-end test for `process_mercadolibre_event` -> SalesOrder**.
   The function is now fully implemented (178 lines in
   `backend/src/api/v1/endpoints/webhooks.py:120`) but unexercised
   against a real ML order payload. Build a fixture posting a realistic
   webhook to `/api/v1/webhooks/mercadolibre`, run the background task
   synchronously, assert `SalesOrder` + `SalesOrderItem` + decremented
   `InventoryItem` + `WebhookEvent.status == "PROCESSED"`.

2. **`MercadoLibreConnector.publish_listing()` still stubbed**. Returns
   `"MLM-STUB-123"`. Next: `POST /items` with full payload, `site_id=MLM`.

3. **Backend error message localization**. Endpoints still emit raw
   English strings (e.g. allocation PATCH used to do this; similar
   patterns elsewhere). Switch to `{"detail": {"code": "...", "params":
   {...}}}` so the frontend can resolve Spanish copy.

### Smaller pre-existing
4. `AmazonConnector.fetch_all_listings()` returns one hardcoded stub.
5. Frontend vitest setup is broken (`resolveComponentResources()` error
   on every spec) — pre-existing Angular 21 + vitest issue.
6. `ng serve` NG0203 (`inject() must be called from an injection
   context`) — currently worked around via custom static server.
7. The `lineItemCountSingular` / `lineItemCountPlural` keys are a
   workaround for the existing `purchaseOrders.lineItems` key.
   Clean up to a single ICU plural.

### Out-of-scope architectural
8. `process_mercadolibre_event` resolves credentials by
   "most-recently-updated for that marketplace" — fine for single-tenant
   but needs work if Fulcrum ever supports multiple users with their own
   ML accounts.

## State Of Existing Worktrees

When you read this:

- `/home/nickvander/fulcrum/.claude/worktrees/musing-torvalds-dc0d74/`
  has stale uncommitted edits (a previous version of the slice 86 file,
  the same `sync_inventory` real-implementation, dead-code delete, and
  PROGRESS.md/MISSING_ITEMS.md edits that describe a stale picture).
  Those uncommitted changes are now superseded by this branch. Safe to
  `git stash drop` / discard.
- `/home/nickvander/fulcrum/.claude/worktrees/lucid-shirley-fb162f/`
  contains the original 6 commits but should be abandoned — the useful
  ones are now on `feature/sales-orders-cherry`, and the rest is dead.
- `/home/nickvander/fulcrum/.claude/worktrees/beautiful-greider-fe0c7d/`
  is stale (its tip `1d7d63c` is now on origin/main + 1 more commit).

## Recommended Next Move

Land the feature branch (`git push origin
feature/sales-orders-cherry:main`), then start a session focused on the
ML webhook E2E test (#1 above). The test will exercise the entire
allocation-replacement story: a real ML order arrives, gets parsed into
a `SalesOrder`, decrements `InventoryItem`, and the dashboard's "Sales
by Channel" widget reflects the new data.
