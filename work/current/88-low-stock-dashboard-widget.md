# 88: Low-Stock Dashboard Widget

## Goal

The dashboard already had a "Critical Stock" widget, but it filtered
products with a hard-coded `stock < 5` check, ignored every configured
threshold (per-product or store-wide default), didn't show velocity or
days-of-inventory, and offered no path to act on what it surfaced. This
slice replaces it with a real reorder report that an operator can use
day-to-day.

## What landed

Commit `ecff79c` — "Replace dashboard low-stock widget with a real
reorder report".

### Backend

- New columns on `products`:
  - `reorder_point` (int, nullable)
  - `reorder_quantity` (int, nullable)
  - Alembic migration `d4e5f6a7b8c9`. Wired into create/update schemas
    so users can tune them without a backend deploy.
- New endpoint `GET /api/v1/reports/low-stock` returning per-product
  rows plus critical/low/watch counts.
  - Threshold precedence (highest first):
    1. `Product.reorder_point`
    2. `ProductInventorySettings.low_stock_quantity_threshold`
    3. `StoreSettings.low_stock_quantity_default` (always set)
  - 25% buffer above the threshold becomes the early-warning "watch"
    band. `on_hand == 0` is "critical". Anything in between is "low".
  - Suggested reorder qty:
    - `Product.reorder_quantity` if set
    - else `max(30 * daily_velocity, threshold * 2)` so even
      slow-moving SKUs get a usable batch suggestion.
  - Daily velocity reuses the existing
    `inventory_service.calculate_sales_velocity` (30-day window by
    default; query-param tunable).
  - Rows sorted by severity then by days-of-inventory ascending.
- New router prefix `/reports/`.

### Frontend

- New `LowStockService.getLowStock(limit, velocityWindowDays)`.
- `LowStockListWidgetComponent` rewritten:
  - Takes a `LowStockReport` (was `Product[]`).
  - Renders a proper table: Product | On hand | Threshold | Velocity |
    Days left | Suggested | Create-PO action.
  - Severity chips (`critical`/`low`/`watch`) at the top reflect the
    summary counts.
  - Per-row "Create PO" button links to
    `/suppliers/po/create?product_id=X`. The PO edit page already
    auto-fills the line item from that query param, so the dashboard
    → PO flow is one click.
- `DashboardComponent` fetches the report directly from the new
  endpoint; the broken client-side `< 5` filter is gone.
- Full en + es-MX translations.

## Verification

- 10 new backend tests in `tests/test_low_stock_report.py` covering:
  - critical (zero stock) classification
  - product reorder_point precedence
  - fall-through to ProductInventorySettings
  - fall-through to store default
  - well-stocked products excluded
  - watch-band classification
  - explicit reorder_quantity respected
  - fallback suggested qty when reorder_quantity unset
  - summary counts
  - severity-then-days-of-inventory ordering
- 7 rewritten frontend specs in `low-stock-list.component.spec.ts`
  covering empty state, table rendering, Create-PO link href, severity
  chips, velocity/days-left formatting edge cases.
- `dashboard.component.spec.ts` patched with a `LowStockService` mock.
- `ng build` green.
- Manually verified in real Chromium against a mixed-severity seed
  (TEA out, COFFEE+PEN low, MUG watch, BAG hidden):
  - Severity chips read "1 out of stock · 2 low · 1 watch"
  - Table renders all four rows with correct on_hand / threshold /
    velocity / days-left / suggested values
  - Click "Create PO" on Earl Grey → lands on
    `/suppliers/po/create?product_id=1` with the product auto-added
    and snackbar "Added Earl Grey Tea to order".

## Open follow-ups

- Reorder fields (`reorder_point`, `reorder_quantity`) aren't yet
  editable from the product form. Today they can only be set via API.
- "Reorder workflow (shopping-cart style)" from the usability roadmap
  — group selected low-stock products by supplier and create one draft
  PO per supplier in a single pass — is the natural next step.
