# 80: Quick Wins & AI Catalog Import

> **STATUS as of 2026-05-17:** Low Stock Widget complete (incl. editable
> reorder fields and shopping-cart-style bulk reorder); Export Service
> first slice (CSV for the low-stock report) just landed. AI Catalog
> Import remains open.

## Summary

Implement high-value features: Low Stock Dashboard Widget, Export Service for
reports, and AI-powered Catalog Import (PDF-first, leveraging existing PO
parsing patterns).

## Acceptance Criteria

- [x] **Low Stock Widget shows products below reorder point on Dashboard**
      — done across `ecff79c` (initial widget), `ef6e90b` (editable reorder
      fields on product form), and `69f2c11` (shopping-cart-style bulk PO
      creation by primary supplier).
- [x] **Export Service generates CSV** for the low-stock report — done in
      this slice (`/api/v1/reports/low-stock/export`, "Export CSV" button
      on the widget header, downloads `fulcrum-low-stock-<date>.csv`).
- [ ] **Export Service generates PDF** — deferred; needs a PDF library
      choice (reportlab vs. weasyprint vs. external service). CSV covers
      the most common "give it to my accountant" use case; PDF is a
      polish item.
- [ ] **AI Catalog Import parses PDF catalogs (multi-page supported)**
      — open. Leverage existing patterns in
      `backend/src/services/purchase_order_ingestion_service.py` and
      `backend/src/api/v1/endpoints/purchase_orders.py:/imports/reviews`
      (the supplier-document import-review flow). The catalog-import case
      is similar shape but produces new Products instead of a PO.
- [ ] **User can preview extracted data before bulk importing** — depends
      on AI Catalog Import.

## Technical Approach

### Low Stock Widget — DONE

| File                                      | Status |
| ----------------------------------------- | ------ |
| `backend/src/api/v1/endpoints/reports.py` | Done — `/reports/low-stock` exists with severity-then-days ordering, threshold precedence, suggested reorder qty |
| `frontend/src/app/dashboard/widgets/low-stock-list/` | Done — `LowStockListWidgetComponent` with table, severity chips, per-row Create-PO, multi-select bulk reorder, CSV export |
| `frontend/src/assets/i18n/*.json`         | Done — full `dashboard.lowStock.*` + `apiErrors.purchaseOrder.reorderEmptySelection` |

### Export Service — PARTIAL (CSV done, PDF deferred)

| File                                      | Status |
| ----------------------------------------- | ------ |
| `backend/src/api/v1/endpoints/reports.py` | Done — `GET /reports/low-stock/export` streams CSV via `StreamingResponse`, date-stamped filename, default limit 500 (cap 5000) |
| `frontend/src/app/dashboard/services/low-stock.service.ts` | Done — `exportLowStockCsv(limit, days)` returns `Blob` |
| `frontend/src/app/dashboard/widgets/low-stock-list/` | Done — "Export CSV" button on widget header, `<a download>` trigger to avoid navigating away |
| PDF generation | **Open** — pick a lib (reportlab is pure-Python, weasyprint needs system fonts). Likely scope: one slice per report type. |
| Export of other reports (sales-by-channel, inventory health, etc.) | **Open** — extend the same pattern when a new report needs export |

### AI Catalog Import (PDF-First) — OPEN

| File                                                     | Status |
| -------------------------------------------------------- | ------ |
| [NEW] `backend/src/services/adk/agents/catalog/`         | Open  |
| `backend/src/api/v1/endpoints/ai.py`                     | Open  |
| [NEW] `frontend/src/app/products/catalog-import-dialog/` | Open  |

**Supported PDF Types:**

- Price lists (SKU, Name, Price tables)
- Product catalogs (multi-page)
- Invoices/Quotes (already covered by the supplier-document import flow
  in `purchase_orders.py`)

## Future Enhancements

- [ ] Website URL scraping for supplier product pages
- [ ] CSV column auto-mapping with AI suggestions

## Verification Plan

- [x] Backend: `docker compose -f docker-compose.test.yml exec backend python -m pytest`
       — backend currently 347/0/6 (2 new CSV-export tests)
- [x] Frontend: `npx ng test --watch=false` — 413/0/14, no regressions
- [ ] Manual: Test PDF upload with sample supplier catalog (pending AI Catalog Import)
