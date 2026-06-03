# 08 — Inventory Operations Improvement Plan

> North star (founder): *"It should be easy to receive products and then add them to the warehouse."*
> Make inventory operations PLEASANT and EASY, consistent with the just-shipped product-list redesign language (outline status pills, consolidated toolbar + one `Agregar ▾` split button, signals/OnPush, skeletons, CDK virtual scroll, token-only SCSS).

Scope: RECEIVING (goods-in → warehouse), INVENTORY COUNT (cycle count / audit), STOCK TRANSFERS (warehouse → ML Full), MANUAL ADJUSTMENTS + HISTORY, plus the cross-cutting toolbar/pill/token alignment.

Priority legend: **P0** = high-impact quick win, low structural risk (ship first) · **P1** = medium · **P2** = larger/structural.

---

## 1. Executive summary

Fulcrum's core loop is **supplier → receive into Bodega (`default`) → send to ML Full → ML fulfills.** The plumbing for this loop already exists and the count flow in particular is genuinely well-built (scan-driven, mobile-aware, safe confirm-on-commit). But the surfaces that *move stock* are the least finished in the app, and three things actively make the loop harder than it should be:

1. **Receiving is the highest-traffic surface and the weakest.** The receiving dialog has no "receive everything" master action (you adjust N fields even when the whole order arrived as ordered), no scan-to-receive, raw `type="number"` inputs (wrong mobile keyboard, spinner noise), over-receipt is silently labelled a "bonus", and — worst — **the core receive action gives no success toast and swallows errors in `console.error`.** An operator can complete a receive, see nothing, and walk away while stock silently failed to post. The destination warehouse is never named, so an ML-Full seller can't tell received stock is in the Bodega and not yet at Full.

2. **Stock can be sent to Full that you don't physically have.** The create-transfer dialog never loads warehouse on-hand and lets you plan any quantity. The `stock-transfer-planner` does this correctly (caps at on-hand) but is buried as a secondary button — two peer entry points with diverging guarantees.

3. **Manual adjustments are unauditable and unguarded.** Reason is optional free-text (no reason codes), there's no large-delta guard, the dialog never says *which location bucket* it's touching, and it allows a resulting-negative stock. One fat-finger is unrecoverable shrinkage with no "why" on record.

4. **Three surfaces regress against the shipped product-list language.** The PO list and transfers list still show the red mini-FAB / peer-button clusters the redesign killed, status is rendered as raw enums (`in_progress`) or hardcoded hex in `.ts` (bypassing the theme guard) or M3-inert `mat-chip [color]`, and the carefully-built 3-bucket vocabulary ("A la mano / MercadoLibre Full") lives on exactly one screen while every stock-moving surface shows raw keys like `default → ml-full`.

5. **The word "audit" means two unrelated things** (the count *session* vs the adjustment *ledger*), and OnPush/signals is absent across every in-scope component despite being the project standard.

**Target experience:** the 90% case (everything arrived as ordered) is **one tap to receive**, you can scan a label to jump to a line, you always see *"Agregaste N unidades a Bodega"* with an **Undo**, you can never ship more to Full than you hold, every adjustment carries a reason code and a confirmable before/after, and every status reads as the same outline pill (icon + word + color) in the same tokens as the product list — so the whole app feels like one product.

---

## 2. The redesigned "receive → warehouse" happy path

Goal: zero typing for the common case; scanning and per-line adjust as the exception; an unmistakable, reversible confirmation that names the destination.

**Ideal flow:**
1. **Enter from a worklist.** Compras → Órdenes de Compra opens with a clickable **"Por recibir" (N)** filter chip (the `Pendiente` KPI becomes a filter, not décor). New users on a `draft` PO see an inline hint: *"Confirma el pedido para poder recibir."*
2. **Open the PO**, click **Recibir** (sticky, only when status ≠ draft).
3. **Dialog opens pre-filled to remaining qty per line.** A single primary button **`Recibir todo lo pendiente`** (the one sanctioned `--primary-color` moment) commits the whole shipment. Header states destination explicitly: **`Recibir en: Bodega (predeterminado)`**.
4. **Scan or adjust the exceptions only.** A **Escanear** button (lifted from the count flow's `ScanSkuDialogComponent`) focuses the matched line and increments it. For partials, each line has a **−/N/+ stepper** (`inputmode="numeric"`, ≥44px targets, `tabular-nums`) and a per-line **"Restante"** affordance to refill.
5. **Over-receipt is a guarded event.** Receiving more than ordered shows a `--warning-color` outline pill **`Excede +N`** (replacing the "bonus" copy) and requires a one-line reason before commit.
6. **Commit → optimistic close + success snackbar with Undo:** *"Agregaste 200 unidades a Bodega · Deshacer"*. Undo wires to the existing `correct` (reversal) path. Errors surface a localized error toast and keep the dialog open with the message — never `console.error` only.
7. **PO detail reflects partial state:** a progress meter *"Recibido 120/200 · 3 SKU pendientes"* and an outline `Parcial` pill, so "what's still coming" is obvious at a glance.

**Loose ASCII sketch of the receiving dialog (mobile-first, single column < 600px):**

```
┌──────────────────────────────────────────────┐
│  Recibir — OC #1043            Proveedor Acme  │
│  Recibir en:  ▣ Bodega (predeterminado)        │   ← destination, always shown
│  ────────────────────────────────────────────  │
│  [ 📷 Escanear ]              Recibido 0 / 200  │   ← scan = accent; progress
│  ────────────────────────────────────────────  │
│  ▣ Tornillo M4  · SKU TRN-M4 · var: 10mm        │
│    Pedido 100 · Restante 100                     │
│        [ − ]  [   100   ]  [ + ]   (Restante)    │   ← stepper, inputmode=numeric
│  ────────────────────────────────────────────  │
│  ▣ Tuerca M4   · SKU TUE-M4                      │
│    Pedido 100 · Restante 100                     │
│        [ − ]  [   105   ]  [ + ]                 │
│        ⚠ Excede +5   (motivo requerido) [____]   │   ← --warning outline pill
│  ────────────────────────────────────────────  │
│  [ Cancelar ]            ⬤ Recibir todo (200)    │   ← sticky; primary = chile-red
└──────────────────────────────────────────────┘
        ↓ commit
  ✔ Agregaste 200 unidades a Bodega · [ Deshacer ]   ← snackbar + undo
```

Tokens: primary button `--primary-color`; scan/stepper/links `--accent-color`; over-receipt pill `--warning-color` (`--bg-raised` fill + 1px border + icon); spacing `--space-*`, radii `--radius-*`, motion `--dur-*`/`--ease-standard`.

---

## 3. Per-flow recommendations

### 3.1 Receiving

**KEEP** — remaining-qty prefill (`receiving-dialog.component.ts:65,76`); the separate `correct`/reversal mode; per-card product image/SKU/variant context; full i18n coverage of `purchaseOrders.receivingDialog.*`.

**FIX**
- **No success toast + silent error** (`receiving-dialog.component.ts:154` close, `:168` `console.error`). Add a localized success snackbar that *names the destination* — "Agregaste {n} unidades a Bodega" — and a localized error toast that keeps the dialog open. The invoice-match path already toasts (`purchase-order-edit.ts:1298`); match it.  **[P0]**
- **No master "Recibir todo"** action. Add a primary button that sets every line = remaining and commits. `--primary-color`.  **[P0]**
- **Over-receipt "bonus"** (`receiving-dialog.component.html:63-67`, `.scss:166`). Replace with `--warning-color` outline pill `Excede +N` + required reason before commit.  **[P1]**
- **Raw `type="number"`** (`receiving-dialog.component.html`). Replace with `type="text" inputmode="numeric"` + horizontal −/N/+ stepper; ≥44px targets; `tabular-nums`.  **[P1]**
- **Destination invisible.** Add a "Recibir en: Bodega (predeterminado)" header reusing the product-list bucket key `products.bucketDefault`.  **[P1]**
- **Dialog responsiveness** (`receiving-dialog.component.scss:1` `min-width:600px` vs warehouse tablets). Single-column < 600px, sticky submit bar.  **[P2]**
- **`correct`-mode prefilled reason** (`receiving-dialog.component.ts:46`) — require an explicit reason for reversals.  **[P2]**

**ADD**
- **Scan-to-receive** — lift `inventory-count/components/scan-sku-dialog/` to a shared component; scan focuses + increments the matched line.  **[P1]**
- **"Por recibir" worklist** — make the `Pendiente` KPI a filter into ordered-but-unreceived POs (`purchase-order-list`); inline "confirma el pedido para recibir" hint on draft POs.  **[P1]**
- **Per-PO progress meter + `Parcial` pill** on PO detail using `quantity_received`/`quantity_ordered` (`purchase-order-edit`).  **[P1]**

**New i18n keys (both `es-MX.json` + `en.json`, tú-form):** `purchaseOrders.receivingDialog.receiveAll` ("Recibir todo lo pendiente"/"Receive all remaining"), `.destinationLabel` ("Recibir en"/"Receive into"), `.exceedsPill` ("Excede +{n}"/"Exceeds +{n}"), `.exceedReasonRequired`, `.successAdded` ("Agregaste {n} unidades a {location}"), `.errorReceiving`, `.undo` ("Deshacer"), `purchaseOrders.list.awaitingReceipt` ("Por recibir"), `purchaseOrders.detail.receivedProgress` ("Recibido {received}/{ordered} · {pending} SKU pendientes"). Remove/repurpose `purchaseOrders.receivingDialog.bonus`.

### 3.2 Inventory Count

**KEEP** — scan-driven add with native `BarcodeDetector` + polyfill and graceful degradation (`scan-sku-dialog.component.ts:82-101`); mobile tap-target work (`detail.scss:104-148`); confirm-on-commit + confirm-on-cancel, commit gated to >0 (`detail.ts:243-281`, `html:162`); inline no-dialog start that routes into the session (`list.ts:95-115`); save-on-blur count input. Count and audit are **complementary, not redundant — cut nothing.**

**FIX**
- **Status renders raw enum** `in_progress` instead of `statusInProgress` labels (`inventory-count-list.component.html:78`, `detail.html:32`). Localize + adopt the outline pill. Most visible polish bug.  **[P0]**
- **es-MX copy bug** — `inventoryAudit.subtitle` "en el espacio" (literal of "in the workspace") → "en tu inventario" (`es-MX.json`).  **[P0]**
- **Reason codes unlocalized / hardcoded English** — `inventory-audit.component.ts:177-181` `reasonCodeLabel()` returns "Uncategorized"/"Recount". Drive off an i18n map.  **[P2]**
- **Count-input error has no rollback** (`detail.ts:192`) — on PATCH failure the field keeps the bad value while the server has the old one. Roll back + show per-row state.  **[P2]**
- **OnPush missing** on all four components incl. `scan-sku-dialog` (its `markForCheck()` calls are no-ops on Default CD).  **[P1]**
- **Radius tokens** — `border-radius: 4px` literals (`detail.scss:130,138`) → `--radius-sm`/`--radius-xs`.  **[P2]**

**ADD / CONSIDER**
- **Blind-count default** (hide `Esperado` until commit) with an "informed" opt-in toggle (`detail.html:100-103`) — reduces anchoring; founder decision (see §6).  **[P2]**
- **Variance threshold + recount flag at commit** — split lines into within-tolerance (auto-post) vs out-of-tolerance (`Revisar` pill, `--warning-color`) before posting (`detail.ts:243`).  **[P2]**
- **Running variance summary** ("18/40 contados · 3 con diferencia · neto −4") sticky header; deep-link commit snackbar to the resulting ledger rows.  **[P2]**
- **Disambiguate IA/vocabulary** — stop using "audit" for both concepts; "Conteo físico" (session) + "Historial de ajustes" (ledger); move ledger under `/inventory/...`; cross-link bidirectionally (`bottom-nav.ts:41`, `sidenav.ts:72`, `viewAuditLink` key).  **[P1]**

**New/changed i18n keys:** use existing `inventoryCount.list.statusInProgress` etc. on rows; fix `inventoryAudit.subtitle` (es); add `inventoryAudit.reason.*` map (recount/uncategorized/damaged/...); `inventoryCount.detail.varianceSummary`, `.reviewPill` ("Revisar").

### 3.3 Stock Transfers (→ ML Full)

**KEEP** — `partially_received` lifecycle modeling end-to-end; `receive-transfer-dialog` `remaining` cap (`receive-transfer-dialog.ts:82`); per-transfer "Reconcile now" poll (`stock-transfer-detail.ts:207-235`); the **planner** as the best surface for the core job (3 buckets + on-hand cap, `stock-transfer-planner.html:61-118`).

**FIX**
- **Create dialog has no on-hand guard** (`stock-transfer-create-dialog.ts:120-123`) — lets you ship to Full more than you hold. Load warehouse on-hand per product; cap/warn like the planner (`[max]="row.internal"`). **Core-loop correctness.**  **[P0]**
- **Raw location keys in route columns** (`stock-transfer-list.html:76-78`, `stock-transfer-detail.html:17-19` render `<code>default</code> → <code>ml-full</code>`). Render friendly labels reusing product-list bucket keys; show source framing "A la mano → MercadoLibre Full ⚡" with `--ml-yellow` only on the Full chip.  **[P1]**
- **Status chips color-only / M3-inert / `draft`==`received` same color** (`stock-transfer-list.html:67`, `.ts:106-120`). Adopt the outline status-pill (icon + word + color, non-redundant).  **[P1]**
- **List toolbar = 3 peer buttons incl. red primary** (`stock-transfer-list.html:8-34`). Consolidate to redesign toolbar + single `Agregar ▾` split button; demote red.  **[P1]**
- **`*matCellDef="let t"` shadows Transloco `let t`** (`stock-transfer-list.html:61`) → rename to `let row`.  **[P2]**
- **Split i18n prefixes for one dialog** — `stockTransfers.createDialog.*` (template) vs `stockTransfers.stockTransferCreateDialog.*` (`.ts:156`); detail borrows `createDialog.notesLabel` (`stock-transfer-detail.html:50`). Consolidate to one namespace.  **[P2]**
- **OnPush missing** on all six transfer components.  **[P1]**

**ADD / CONSIDER**
- **In-transit feeds the product "+N en camino" hint** — render `En tránsito` qty as inbound on the product, answering the product-list "¿Por qué 0 disponible?" explainer.  **[P2]**
- **Reconciliation as variance grammar** — frame sent-vs-confirmed like count variance with a `Discrepancia +N/−N` `--warning-color` pill; signpost "poll this shipment" vs "discrepancy report".  **[P2]**
- **Planner suggests what to send to Full** ("low on Full, in stock in Bodega"); promote planner as the primary create path / merge the dumb create-dialog into it.  **[P2]**

**New i18n keys:** reuse `products.bucketDefault`/`products.bucketMlFull`; add `stockTransfers.overAllocateWarning` ("Solo tienes {n} a la mano"), `stockTransfers.status.*` pill labels, `stockTransfers.reconcile.discrepancy` ("Discrepancia {delta}"). Align `stockTransfers.planner.col.*` to the product-list bucket vocabulary.

### 3.4 Manual Adjustments + History

**KEEP** — two-step preview→confirm (`stock-adjustment-dialog.ts:54-66`); before/after "Nuevo stock" panel (`html:24`); stock-history signed coloring + PO-linkify (`stock-history-dialog.ts:51-64`).

**FIX**
- **No reason codes** (`stock-adjustment-dialog.html:13-16` free-text optional). Replace with a **required** reason-code select (Dañado, Robo/merma, Error de captura, Recepción, Devolución, Conteo) + optional note.  **[P0]**
- **Location-blind** — `StockAdjustmentData` is only `{productName, currentQuantity}` (`stock-adjustment-dialog.ts:11-14`). Add `location`; show which bucket; note that adjusting `default` doesn't change ML-Full availability.  **[P0]**
- **Allows resulting-negative stock** — `confirmAdjustment()` blocks `0` but not a negative result. Block it.  **[P0]**
- **No large-delta guard** — add a `--warning-color` caution (or extra typed confirm) when `|adjustment|` exceeds a threshold (>current stock or > N units).  **[P2]**
- **`isPoReason` matches English literal** `'Received PO #'` (`stock-history-dialog.ts:52`) — i18n landmine; drive PO-linkify off a structured field.  **[P1]**
- **Raw `rgba(0,0,0,0.1)` box-shadow** (`stock-history-dialog.component.scss:72`) → `var(--shadow-sm)` (fails contrast guard).  **[P2]**
- **OnPush missing** on both dialogs.  **[P1]**

**ADD** — every receive correction, count commit, transfer, and manual adjust writes an `InventoryAdjustment` row with {who, when, reason code, delta, location, source} into one unified `stock-history-dialog` timeline.  **[P2]**

**New i18n keys:** `stockAdjustment.reason.*` (damaged/theft/dataEntry/received/return/count), `stockAdjustment.reasonRequired`, `stockAdjustment.locationLabel`, `stockAdjustment.mlFullNote`, `stockAdjustment.negativeBlocked`, `stockAdjustment.largeDeltaWarning`.

---

## 4. Consistency fixes vs the product-list language

Specific offenders found (all should converge on the shipped pattern: consolidated toolbar + one `Agregar ▾` split button, outline status pills, skeletons, CDK virtual scroll where unbounded, token-only):

- **PO-list red mini-FAB cluster** — 5 `mat-mini-fab` (`upload_file/add/business/download/picture_as_pdf`), 2 of them `color="primary"` (`purchase-order-list.component.html:13-34`). Replace with toolbar + single `Agregar ▾` (Importar documento / ingest fold into the caret). **[P0/P1]**
- **PO-list red KPI cards** — full-bleed red "TOTAL DE ÓRDENES". De-red: neutral surfaces (`--bg-card`/`--text-main`); color only for real states. Make `Pendiente`/`Recibido` clickable filters. **[P1]**
- **Hardcoded hex status colors in `.ts`** (bypass `check_theme_contrast.py`): `purchase-order-list.component.ts:417-419` `getReviewStatusColor()` (`#4caf50/#c62828/#ff9800`) and `:595-601` `getStatusColor()` (`#9e9e9e,#ff9800,#2196f3,#4caf50,#607d8b`), injected via `[style.background-color]`; `import-review-panel` inline `+ '22'` tint (`html:190-195`); `purchase-order-edit.html:139` raw hex fallback. Map to `--success/-warning/-error/-accent/-text-hint` via CSS classes. **[P1]**
- **Count status raw enum** `{{ row.status }}` (`inventory-count-list.component.html:78`, `detail.html:32`) → localized outline pill. **[P0]**
- **Transfers status `mat-chip [color]`** (M3-inert, `draft`==`received`) (`stock-transfer-list.html:67`) → outline pill. **[P1]**
- **Transfers 3-peer-button toolbar incl. red primary** (`stock-transfer-list.html:8-34`) → consolidated toolbar. **[P1]**
- **stock-history `rgba()` shadow** (`stock-history-dialog.component.scss:72`) → `var(--shadow-sm)`. **[P2]**
- **3-bucket vocabulary divergence** — product-list `products.bucketDefault/MlFull/AmazonFba` is reused nowhere stock moves; planner re-spells it, transfers/adjust show raw keys or nothing. Standardize on the product-list keys everywhere. **[P1]**
- **Skeletons + virtual scroll** — count list, transfers list, audit ledger use spinners + plain `mat-table` (ledger is unbounded). Add skeleton rows + CDK virtual scroll on the ledger. **[P2]**
- **OnPush/signals absent** across every in-scope component (receiving-dialog, purchase-order-list, purchase-order-edit, all 6 transfer components, both product dialogs, all 4 count/audit components). **[P1]**
- **Routing** — count/audit use legacy NgModule routing (`app-routing.module.ts`, `products-routing.module.ts`) vs the standalone `*.routes.ts` pattern. **[P2]**

---

## 5. Prioritized, tiered backlog

### P0 — ship first (highest impact on "easy to receive", low structural risk)

| # | Task | Files | Effort |
|---|------|-------|--------|
| P0-1 | Success snackbar naming destination + localized error toast (no more silent receive) | `receiving-dialog.component.ts` | S |
| P0-2 | "Recibir todo lo pendiente" master button | `receiving-dialog.component.{ts,html,scss}` | S |
| P0-3 | Localize count status (drop raw `in_progress`) | `inventory-count-list.component.html`, `inventory-count-detail.component.html` | S |
| P0-4 | Fix `inventoryAudit.subtitle` "en el espacio" → "en tu inventario" | `assets/i18n/es-MX.json` | S |
| P0-5 | On-hand guard in create-transfer dialog (cap/warn like planner) | `stock-transfer-create-dialog.{ts,html}` | M |
| P0-6 | Required reason-code select on adjustments | `stock-adjustment-dialog.{ts,html}`, i18n | S |
| P0-7 | Adjustment shows location bucket + blocks resulting-negative stock | `stock-adjustment-dialog.{ts,html}` | S |
| P0-8 | De-red + consolidate PO-list toolbar (kill 6 mini-FABs → `Agregar ▾`) | `purchase-order-list.component.{ts,html,scss}` | M |

### P1 — medium

| # | Task | Files | Effort |
|---|------|-------|--------|
| P1-1 | Over-receipt `Excede +N` warning pill + required reason (replace "bonus") | `receiving-dialog.component.{ts,html,scss}`, i18n | M |
| P1-2 | Replace `type="number"` with `inputmode="numeric"` + −/N/+ stepper (receive, count, adjust) | receiving-dialog, inventory-count-detail, stock-adjustment-dialog `.html` + shared stepper | M |
| P1-3 | Lift `scan-sku-dialog` to shared; add scan-to-receive | `inventory-count/components/scan-sku-dialog/` → shared, `receiving-dialog.*` | M |
| P1-4 | Destination header + "Por recibir" worklist filter + draft hint + PO progress meter | `receiving-dialog.*`, `purchase-order-list.*`, `purchase-order-edit.*` | M |
| P1-5 | Map all hardcoded `.ts` hex status colors to tokens via CSS classes | `purchase-order-list.component.ts`, `import-review-panel.*`, `purchase-order-edit.html` | M |
| P1-6 | Friendly location labels (reuse bucket keys) on transfer list + detail | `stock-transfer-list.html`, `stock-transfer-detail.html` | S |
| P1-7 | Outline status pills on transfers + count (replace mat-chip/color) | `stock-transfer-list.*`, count list/detail, shared pill | M |
| P1-8 | Consolidate transfers toolbar to single split button; rename `let t`→`let row` | `stock-transfer-list.{ts,html}` | S |
| P1-9 | `isPoReason` off structured field, not English literal | `stock-history-dialog.ts` | S |
| P1-10 | Add OnPush to in-scope components (incremental, per component) | all in-scope components | M |
| P1-11 | Disambiguate count vs audit naming/IA; cross-link | `bottom-nav.ts`, `sidenav.ts`, routes, i18n | M |

### P2 — larger / structural

| # | Task | Files | Effort |
|---|------|-------|--------|
| P2-1 | Optimistic receive close + Undo wired to `correct` reversal | `receiving-dialog.*`, PO service | M |
| P2-2 | Blind-count default + variance threshold/recount flag at commit | `inventory-count-detail.{ts,html}` | M |
| P2-3 | Count error rollback + per-row save state + skeletons | `inventory-count-detail.*`, list `.html` | M |
| P2-4 | In-transit "+N en camino" hint feeding product-list "why 0" | transfers → product-row vm/template | M |
| P2-5 | Reconciliation variance grammar + signpost the two reconcile paths | `stock-transfer-reconciliation.*`, `stock-transfer-detail.*` | M |
| P2-6 | Planner as primary create path / merge create-dialog; send-to-Full suggestions | `stock-transfer-planner.*`, `stock-transfer-create-dialog.*` | L |
| P2-7 | Large-delta guard on adjustments | `stock-adjustment-dialog.{ts,html}` | S |
| P2-8 | Unified InventoryAdjustment history (who/when/reason/location/source) | `stock-history-dialog.*`, backend write paths | M |
| P2-9 | Localize reason codes; radius/shadow token cleanup | `inventory-audit.component.ts`, `inventory-count-detail.scss`, `stock-history-dialog.scss`, i18n | S |
| P2-10 | Skeletons + CDK virtual scroll on ledger; migrate to standalone `*.routes.ts` | count/audit list + ledger, routing | L |
| P2-11 | Receiving dialog responsiveness (single-col <600px, sticky submit) | `receiving-dialog.component.scss` | S |
| P2-12 | Extract receiving/invoice/AI from 1,444-line `purchase-order-edit` god component | `purchase-order-edit.*` | L |

---

## 6. Open questions / decisions for the founder

1. **Blind vs informed count default.** Blind (hide expected until commit) is the accuracy gold standard but slower and feels less "helpful." Default to blind with an informed toggle, or keep informed? (Affects C-flow build.)
2. **Variance/large-delta thresholds.** What numbers? Proposed: count recount-flag at ">10 units OR >5%"; adjustment large-delta warning at ">50% of current OR >N units". Need N and whether out-of-tolerance count lines are *blocked* or just *flagged*.
3. **Over-receipt policy.** Keep allowing over-receipt (with `Excede` warning + reason), or hard-block it? Current code silently allows; recommendation is warn+reason.
4. **Adjustment reason-code taxonomy.** Confirm the list: Dañado, Robo/merma, Error de captura, Recepción, Devolución, Conteo — and whether "approval" is required for large adjustments (single-operator shop may not want it).
5. **Create-dialog vs planner.** OK to merge the dumb create-dialog into the planner model (always shows on-hand), or must both entry points survive?
6. **"Audit" rename + route move.** Approve renaming code identifiers/labels (count = "Conteo físico", ledger = "Historial de ajustes") and moving the ledger from `/products/audit` to `/inventory/history`? (Touches deep links / muscle memory.)
7. **Landed cost in receiving.** Surface per-unit landed cost (freight/duty) at receive confirmation now, or defer? Mexico import duty makes downstream margin math depend on it.
8. **Amazon FBA.** Memory says ML-Full is primary and FBM/storefront future-only — should the 3rd bucket (amazon-fba) be hidden everywhere for now to simplify, or kept visible?
