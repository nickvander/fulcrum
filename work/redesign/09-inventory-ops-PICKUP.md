# Inventory Operations — PICKUP / Handoff

> Resume doc for the inventory-operations overhaul. Read this first to continue cold.
> Last updated after commit `c427c45` (2026-06-03). North star (founder):
> **"It should be easy to receive products and then add them to the warehouse."**

Companion docs: the full audit + tiered plan is `08-inventory-ops-audit.md`
(§5 backlog, §6 founder decisions, §7 shipped progress log). The product-list
redesign that established the shared visual language is `07-product-list-redesign-spec.md`.

---

## 1. Current state (all SHIPPED + PUSHED to origin/main)

Frontend suite: **914 tests passing** (143 files). Every tranche below passed
theme guard + i18n parity + `ng build` + the full suite, with new unit tests for
all new logic.

| Commit | What |
|---|---|
| `50965bc` | **P0** receive success/error toasts (killed silent-failure), "Recibir todo", create-transfer on-hand guard, adjustment reason-codes+location+block-negative, count status localized, PO toolbar→split button |
| `ed121cf` | **P1a** PO-list hex→token status pills, transfers outline pills + friendly bucket labels + `let t` shadow fix, over-receipt "Excede +N" pill+reason |
| `e5c83c7` | **P1b** shared `QuantityStepperComponent` → receive/adjust/transfer |
| `84e9d73` | **P1c** ledger nav → "Historial de ajustes"; adjustment OnPush |
| `531a652` | **P1d** PO receiving progress meter ("Recibido X/Y") |
| `fe090a8` | **P1-4/FBA** "Por recibir" worklist chip; hide Amazon FBA; first `product-row.vm.spec.ts` |
| `90cd33a` | **P1-3** scan-to-receive (`applyScannedCode` matches PO line by SKU/barcode/QR/variant) |
| `88cec08` | **P2-2** count variance flag (>10u OR >5% → "Revisar" + commit warning) |
| `598c8e8` | **P2-9** localized adjustment reason codes + stock-history shadow→token |
| `e3864af` | **P2-11** receiving dialog responsive (single-col <640px, sticky submit) |
| `73b946d` | **P2-1** optimistic receive + Undo (reverses via receive-correction, then refreshes) |
| `c427c45` | docs progress log appended to `08-...md` |
| _(this session)_ | **P2-4** in-transit "+N en camino" on the product list (backend agg + row/card/peek hint) |
| _(this session)_ | **P1-9** structured adjustment `source`/`source_id` → PO-linkify without string-matching (migration `d3f7a1c8e024`) |
| _(this session)_ | **P2-5** `Discrepancia +N/−N` warning pill in stock-transfer-reconciliation (tolerance-gated, in-transit-aware) |

**Status:** all of P0, all of P1, and the contained/testable slice of P2 are done.

---

## 2. Remaining backlog (what to pick up next)

Grouped by why it wasn't done in the incremental tranches:

### Backend-dependent (need a backend change + frontend)
- **P2-4 — in-transit "+N en camino" → product list. ✅ SHIPPED (this session).**
  Backend: `_hydrate_product_list_metrics` in
  `backend/src/api/v1/endpoints/products.py` now adds one batched aggregate —
  `in_transit_qty` = sum of `qty_planned - qty_received` over stock-transfers
  with status `shipped`/`partially_received` and `dest_location='ml-full'`,
  clamped ≥0, exposed on the `Product` schema. Frontend: `ProductRowVM.inTransitQty`
  (clamped) → a `.pill-in-transit` "+N en camino" hint in the table Available
  column, the grid card-foot, and a dedicated row in the "¿0?" stock peek.
  i18n `products.inTransit{Qty,Label,Tooltip}`. Tests: 1 backend (5 scenarios:
  shipped+partial count, draft/received/other-dest ignored, over-receipt clamps)
  + 3 VM specs. Query-count ceiling now ~18 (still <20).
- **P1-9 — structured adjustment source. ✅ SHIPPED (this session).**
  `InventoryAdjustment` gained `source` (machine key, e.g. `'purchase_order'`) +
  `source_id` (origin entity id) — migration `d3f7a1c8e024`, indexed on `source`,
  no CHECK (open set, unlike `reason_code`). New `InventoryAdjustmentSource` enum +
  `record_adjustment`/`adjust_stock` kwargs; PO receive **and** correction stamp
  `(purchase_order, po.id)`. Serialized on the adjustment schema. The dialog's
  `isPoReason` string-match is gone — `isPoAdjustment`/`poId` read the structured
  fields (with a locale-safe fallback to the legacy English `'Received PO #'`
  reason for pre-migration rows). Also fixed the old double-render bug ("Received
  Received PO #5" / mixed-language es). Tests: +2 backend (receive+correction
  stamp; manual = NULL) + 6 dialog specs. The same `source`/`source_id` is the
  hook **P2-8** (unified history) will extend to transfers/counts/orders.
- **P2-8 — unified InventoryAdjustment history.** Every receive-correction, count
  commit, transfer, and manual adjust should write a row with
  {who, when, reason code, delta, location, source} into one timeline. Backend
  write-path work + the `stock-history-dialog` UI.

### Shipped this session (was in this bucket)
- **P2-5 — reconciliation variance grammar. ✅ SHIPPED.** `stock-transfer-reconciliation`
  now flags out-of-tolerance lines with a `Discrepancia +N/−N` `--warning` pill +
  a roll-up summary line, mirroring the cycle-count variance tolerance (>10 units
  OR >5% of shipped). In-transit-aware: an over-receipt counts in any state, but a
  shortfall only flags once the receive window has closed (RECEIVED / CANCELLED) —
  a PARTIALLY_RECEIVED shortfall may still be on its way, so it doesn't cry wolf.
  Frontend-only (`delta` already on the API). +6 unit tests.

### Large refactors (own session each)
- **P2-12 — split the 1,444-line `purchase-order-edit.component.ts`** (extract
  receiving / invoice-match / AI concerns).
- **P2-10 — ledger virtual-scroll + standalone routes migration** (count/audit use
  legacy NgModule routing; ledger uses plain `mat-table`).
- **P2-6 — planner-as-primary** (merge the dumb create-transfer dialog into the
  planner model; add "send to Full" suggestions).
- **P2-3 — count error rollback + per-row save state + skeletons**
  (`inventory-count-detail` save-on-blur currently keeps a bad value on PATCH fail).

### Mechanical (needs per-component visual check, not just tests)
- **P1-10 — OnPush rollout** across the ~12 still-Default in-scope components
  (receiving-dialog, purchase-order-list, purchase-order-edit, the 6 transfer
  components, both count components, scan-sku-dialog). Do one at a time + verify.

### Founder decision pending
- **Blind-count default** (hide `Esperado` until commit). Was NOT among the 4
  approved policy defaults; ask before building. (Variance flagging is already
  shipped — `88cec08`.)

Already-approved founder decisions (applied): over-receipt = warn+reason; the 6
reason codes; hide Amazon FBA; rename audit→Conteo/Historial.

---

## 3. How to run / verify (environment)

Node default is v12 (too old) — **use nvm Node 24**:

```bash
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24
```

- **Build (type+template check):** `cd frontend && npx ng build --configuration development`
- **Full frontend suite (914):** `cd frontend && npm test`   (vitest via `@angular/build:unit-test`)
- **One spec:** `cd frontend && npx ng test --include='**/<name>.spec.ts' --watch=false`
- **Theme guard (must pass; raw hex in component SCSS fails it):**
  `python3 check_theme_contrast.py [path]`
- **i18n parity (en vs es-MX, no missing/dupes):**
  `python3 check_i18n_consistency.py frontend/src/assets/i18n/en.json frontend/src/assets/i18n/es-MX.json`
- **App for screenshots:** `docker compose up -d db backend` (API :8200), seed with
  `docker compose exec -T backend pip install requests` then
  `cat scripts/seed_full.py | docker compose exec -T backend python`, then
  `cd frontend && npx ng serve` (UI :4200, proxies /api → :8200). Login
  `admin@example.com` / `SecurePass123!`. Capture screenshots to
  `work/redesign/shots/step8-inventory/`.
- Pre-commit hook runs fast backend pytest + ruff + i18n + theme guard; pre-push
  runs the **full frontend suite** too. Never `--no-verify` (it's denied anyway).

---

## 4. Conventions & gotchas (so the next change matches)

- **Shared status pill:** `.status-pill` + `.st-success/-warning/-error/-info/-neutral`
  (outline: `--bg-raised` fill + 1px border + colored icon/text). Defined per-
  component SCSS in PO-list, transfers list. Stock/ML/reorder pills in the product
  list use `.pill` variants. Always icon + word + color (non-color-redundant).
- **Brand discipline:** `--primary-color` (chile-red) = primary button + destructive
  only; `--accent-color` (blue) = all other interactive chrome; `--ml-yellow` =
  the "Full" chip/bolt only.
- **i18n:** add keys to BOTH `es-MX.json` and `en.json` (tú-form es-MX). The repo
  edits these via a small Python deep-merge (see prior commits) to keep parity;
  the harness needs a Read before Edit on these big files.
- **Tokens:** `--space-1..8` (4px scale), `--radius-xs/sm/md/lg/pill`,
  `--dur-fast/base` + `--ease-standard`, `--shadow-sm/md/lg`. No raw hex / rgba on
  color/bg/border in component SCSS (box-shadow is exempted by the guard but
  prefer `var(--shadow-*)`).
- **Reusable bits added this program:** `QuantityStepperComponent`
  (`shared/components/quantity-stepper/`, OnPush, `[value]/(valueChange)`,
  `[min]/[max]`, `inputmode=numeric`); `ProductRowVM` + `toRowVM`
  (`products/components/product-list/product-row.vm.ts`, has its own spec).
- **Bash gotcha:** the tool's shell cwd persists between calls and drifts after a
  failed `cd`. Always `cd /home/nickvander/fulcrum/frontend && …` with an absolute
  path before `npx ng …`.
- **Test gotcha:** the global DateRangeService applies a default date range; PO-list
  filter tests must null `component.startDate/endDate` before `applyFilters()`.
  Compute on-demand values (e.g. transfer on-hand) at action/render time, not at
  `ngOnInit`, to avoid module-load-order flakiness across the full suite.

---

## 5. Suggested first move next session
P2-4, P1-9, and P2-5 all shipped this session. Best next pick:
- **P2-8 (unified history)** — now unblocked: `InventoryAdjustment` already has
  `source`/`source_id` (from P1-9). Extend the `InventoryAdjustmentSource` enum +
  stamp it on the remaining write paths (transfers, count commit, order ingestion,
  returns) so every movement carries a structured origin, then build the unified
  timeline UI. Larger backend write-path item — its own session.

Other contained picks: P2-3 (count error rollback + per-row save state), P2-6
(planner-as-primary), or the mechanical P1-10 OnPush rollout.
