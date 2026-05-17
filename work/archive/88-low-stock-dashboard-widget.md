# 88: Low-Stock Dashboard Widget

> **STATUS: ✅ COMPLETE.** Initial slice landed in `ecff79c`; both
> open follow-ups closed in this session.

## Goal

The dashboard already had a "Critical Stock" widget, but it filtered
products with a hard-coded `stock < 5` check, ignored every configured
threshold (per-product or store-wide default), didn't show velocity or
days-of-inventory, and offered no path to act on what it surfaced. This
slice replaced it with a real reorder report that an operator can use
day-to-day.

## What landed (initial slice — commit `ecff79c`)

### Backend

- New columns on `products`:
  - `reorder_point` (int, nullable)
  - `reorder_quantity` (int, nullable)
- New endpoint `GET /api/v1/reports/low-stock` with severity-then-days
  ordering, threshold precedence:
  1. `Product.reorder_point`
  2. `ProductInventorySettings.low_stock_quantity_threshold`
  3. `StoreSettings.low_stock_quantity_default`
- Suggested reorder qty: `Product.reorder_quantity` or
  `max(30 * daily_velocity, threshold * 2)`.

### Frontend

- `LowStockService.getLowStock` + rewritten `LowStockListWidgetComponent`.
- Per-row "Create PO" deep-link.
- 10 backend + 7 frontend tests, ng build green, manual Chromium check.

## Follow-ups closed this session (2026-05-17)

### 1. Reorder fields editable on the product form (`ef6e90b`)

Added `reorder_point` and `reorder_quantity` as integer inputs in the
Inventory / Pricing card on `product-form`. Validators.min(0) /
Validators.min(1) respectively. Hint copy explains the precedence
("Overrides the store low-stock default") and the velocity-based
fallback ("Defaults to ~30 days of sales"). Wired through the form
group, isDirty check, save payload, Product TS model. 6 new i18n keys
(label / placeholder / hint per field × en + es-MX).

### 2. Shopping-cart-style reorder workflow

Group selected low-stock products by supplier and create one draft PO
per supplier in a single pass.

#### Backend

`POST /api/v1/reports/low-stock/reorder`. Input:

```json
{
  "product_ids": [1, 2, 5],
  "quantity_overrides": { "2": 50 }
}
```

For each product:
1. Find the primary `SupplierProduct` row (tied break by most-recent).
2. Quantity = `quantity_overrides[id]` or `product.reorder_quantity`
   or velocity-based fallback (`max(30 * daily_velocity,
   threshold * 2)` — matches the report's suggestion logic so the
   cart numbers match what the user just saw).
3. Unit cost = `supplier_product.cost_price` or `product.cost_price`.

Products with no supplier mapped are returned in `skipped` with
`reason: "no_supplier"` instead of being silently dropped.

Response:

```json
{
  "created_purchase_orders": [
    { "purchase_order_id": 42, "supplier_id": 1, "supplier_name": "Acme",
      "product_count": 2, "total_amount": 185.00 }
  ],
  "skipped": [
    { "product_id": 5, "product_name": "Orphan", "reason": "no_supplier" }
  ]
}
```

Each PO is created in DRAFT state with notes "Auto-created from
low-stock reorder cart" so it's distinguishable from manually-created
POs and the buyer can review before sending.

5 new backend tests (`tests/test_low_stock_reorder.py`): groups by
supplier into separate POs, quantity overrides, skips products with
no supplier, empty selection returns localized 400
(`apiErrors.purchaseOrder.reorderEmptySelection`), picks primary
supplier when multiple mapped.

#### Frontend

`LowStockService.reorderProducts(ids, overrides?)` POST.

`LowStockListWidgetComponent`:
- New "select" column with per-row checkboxes + a header
  select-all/indeterminate checkbox.
- "Reorder {{count}} selected" button appears in the widget header
  when at least one row is checked.
- On click, calls the endpoint and surfaces results via snackbar:
  - **1 PO created** → success snackbar with a "View PO" action that
    navigates to the draft for review
  - **N POs created** → summary snackbar ("Created 3 draft POs
    covering 7 products")
  - **Any skipped** → second error-styled snackbar with count + the
    first skipped product name as a hint
  - **All skipped** → single error snackbar telling the user no
    supplier is mapped on any of the selected products
- Selection clears + `reordered` event fires after success so the
  parent dashboard can refresh.

`dashboard.component.html` wires `(reordered)="refresh()"` into the
widget so the dashboard data refetches once new POs exist.

9 new i18n keys under `dashboard.lowStock.*` (selectAllTooltip,
reorderSelected, reordering, reorderCreatedOne, reorderCreatedMany,
reorderPartialSkipped, reorderAllSkipped, viewPo) plus the backend
`apiErrors.purchaseOrder.reorderEmptySelection`. All with parity.

## Totals after this session

| Layer | Result |
| --- | --- |
| Backend | 345/0/6 (+5 from 340 after item 8 stopgap) |
| Frontend | 413/0/14 (no regressions) |
| i18n keys with parity | 1152 (+15 across both follow-ups) |
| Production build | clean |

## What's NOT covered

- Per-product quantity edit in the cart UI before submitting (the
  backend accepts `quantity_overrides`, but the widget doesn't expose
  it — submits with the suggested qty). Would need a dialog or
  inline-edit cells. Low priority since the buyer can adjust the
  qty on the draft PO before sending.
- Multi-supplier selection (if a product has 2 suppliers, the user
  can't pick which one). Goes to whoever the row marks as primary.
- "Send PO" automation after creation — POs are intentionally left
  in DRAFT so the buyer reviews first.
