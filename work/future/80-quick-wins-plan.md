# 80: Quick Wins & AI Catalog Import

> **STATUS as of 2026-05-17:** Low Stock Widget complete (incl. editable
> reorder fields and shopping-cart-style bulk reorder); Export Service
> first slice (CSV for the low-stock report) shipped; AI Catalog Import
> **CSV slice** shipped in `8fbb37c` (backend) + `7979156` (frontend).
> Remaining for this initiative: PDF/AI parsing reusing the same review
> shape, and PDF export for reports.

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
- [x] **User can preview extracted data before bulk importing** — done
      in the CSV slice via `/api/v1/catalog-imports/reviews` +
      `CatalogImportDialogComponent` (upload → editable review table →
      approve/reject).
- [ ] **AI Catalog Import parses PDF catalogs (multi-page supported)**
      — open. The review/approve flow already accepts the
      `ExtractedCatalogItem` shape so adding a PDF parser is a backend-
      only follow-up: add `_parse_pdf` to `CatalogIngestionService`,
      reuse the same `extracted_data["items"]` schema, no frontend
      changes required.

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

### AI Catalog Import — CSV SLICE DONE, PDF/AI OPEN

| File                                                                    | Status |
| ----------------------------------------------------------------------- | ------ |
| `backend/src/models/catalog_import.py`                                  | Done — staging row, same shape as `SupplierDocumentImport` |
| `backend/alembic/versions/e2f1a9b73c40_add_catalog_imports.py`          | Done |
| `backend/src/services/catalog_ingestion_service.py`                    | Done — CSV/TSV with EN+es-MX header aliases, ; delimiter, decimal-comma |
| `backend/src/api/v1/endpoints/catalog_imports.py`                       | Done — POST/GET/approve/reject |
| `backend/tests/test_catalog_imports.py`                                 | Done — 11 tests (parser + endpoints + duplicate-SKU skip) |
| `frontend/src/app/products/services/catalog-import.service.ts`         | Done |
| `frontend/src/app/products/components/catalog-import-dialog/`          | Done — 3-step dialog + 8 specs |
| Products page entry button                                              | Done — "Import Catalog" next to Scan/Add |
| **Open:** PDF parser inside `catalog_ingestion_service.py`             | Reuses the same `ExtractedCatalogItem` shape; no frontend changes needed |

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
