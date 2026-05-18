# 80: Quick Wins & AI Catalog Import

> **STATUS as of 2026-05-17 (closed):** Every acceptance criterion in this
> plan is shipped. Low Stock Widget, Export Service (CSV + PDF), and AI
> Catalog Import (CSV + AI-powered PDF/image) are all in production on
> `main`. Remaining ideas (other reports' PDF exports, supplier
> auto-mapping for AI imports) live under "Future Enhancements" and can
> be opened as separate initiatives.

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
- [x] **Export Service generates PDF** — shipped in `4c7c5b7`. Uses
      reportlab (pure Python, no system font deps). Landscape letter
      page, severity-colored rows, same data + limits as the CSV
      export. New `Export PDF` button on the widget header next to
      `Export CSV`.
- [x] **User can preview extracted data before bulk importing** — done
      in the CSV slice via `/api/v1/catalog-imports/reviews` +
      `CatalogImportDialogComponent` (upload → editable review table →
      approve/reject).
- [x] **AI Catalog Import parses PDF catalogs (multi-page supported)**
      — shipped in `cc9b038`. Reuses `InvoiceParserAgent` with a new
      `catalog_extraction.md` prompt (one row per product). PDF /
      image uploads are only accepted when AI is enabled in Settings
      AND the active provider has an API key (checked via
      `ADKManager.is_ready()`). The frontend dialog gates on a new
      `GET /catalog-imports/capabilities` endpoint: yellow "needs AI"
      banner when off, green "AI is configured" banner when ready,
      with the file input's `accept` list adjusted accordingly.

## Technical Approach

### Low Stock Widget — DONE

| File                                      | Status |
| ----------------------------------------- | ------ |
| `backend/src/api/v1/endpoints/reports.py` | Done — `/reports/low-stock` exists with severity-then-days ordering, threshold precedence, suggested reorder qty |
| `frontend/src/app/dashboard/widgets/low-stock-list/` | Done — `LowStockListWidgetComponent` with table, severity chips, per-row Create-PO, multi-select bulk reorder, CSV export |
| `frontend/src/assets/i18n/*.json`         | Done — full `dashboard.lowStock.*` + `apiErrors.purchaseOrder.reorderEmptySelection` |

### Export Service — DONE

| File                                                       | Status |
| ---------------------------------------------------------- | ------ |
| `backend/src/api/v1/endpoints/reports.py`                  | Done — `GET /reports/low-stock/export` streams CSV; `/reports/low-stock/export-pdf` streams a reportlab-rendered landscape PDF with severity-colored rows. Both date-stamped, default limit 500 (cap 5000). |
| `frontend/src/app/dashboard/services/low-stock.service.ts` | Done — `exportLowStockCsv(limit, days)` and `exportLowStockPdf(limit, days)`, both returning `Blob` |
| `frontend/src/app/dashboard/widgets/low-stock-list/`       | Done — `Export CSV` and `Export PDF` buttons share a `downloadBlob` helper so the JWT stays in the Authorization header rather than the URL |
| Export of other reports (sales-by-channel, inventory health, etc.) | **Open** — same `StreamingResponse + reportlab/csv.writer` pattern can extend when a new report needs export |

### AI Catalog Import — DONE

| File                                                                   | Status |
| ---------------------------------------------------------------------- | ------ |
| `backend/src/models/catalog_import.py`                                 | Done — staging row, same shape as `SupplierDocumentImport` |
| `backend/alembic/versions/e2f1a9b73c40_add_catalog_imports.py`         | Done |
| `backend/src/services/catalog_ingestion_service.py`                    | Done — CSV/TSV with EN+es-MX header aliases, `;` delimiter, decimal-comma; `ingest_ai_result()` normalizes the AI agent's JSON into the same `ExtractedCatalogData` shape; low-confidence warning |
| `backend/src/services/adk/agents/invoice/prompts/catalog_extraction.md` | Done — catalog-shaped prompt (one row per product) |
| `backend/src/services/adk/orchestrator.py`                              | Done — `parse_catalog()` reuses `InvoiceParserAgent` with the new prompt |
| `backend/src/services/adk/manager.py`                                   | Done — `ADKManager.is_ready()` single predicate (ai_enabled AND active provider keyed) used by capabilities + upload endpoint |
| `backend/src/api/v1/endpoints/catalog_imports.py`                       | Done — `GET /capabilities`, `POST /reviews` (CSV + AI), GET-list, GET-one, approve, reject |
| `backend/tests/test_catalog_imports.py`                                 | Done — 17 tests (parser + endpoints + duplicate-SKU skip + AI gating) |
| `frontend/src/app/products/services/catalog-import.service.ts`         | Done — `capabilities()` queried on dialog init |
| `frontend/src/app/products/components/catalog-import-dialog/`          | Done — 3-step dialog + AI-status banner (green ready / yellow needs-AI with "Open Settings" link) + dynamic `accept` list; supplier select also available on review step; price/cost cells now `step="0.01"`; 10 specs |
| Products page entry button                                              | Done — "Import Catalog" next to Scan/Add (on the routed `ProductList` component) |

**Supported PDF Types:**

- Price lists (SKU, Name, Price tables)
- Product catalogs (multi-page)
- Invoices/Quotes (already covered by the supplier-document import flow
  in `purchase_orders.py`)

## Future Enhancements

- [ ] Website URL scraping for supplier product pages
- [ ] CSV column auto-mapping with AI suggestions (instead of fixed aliases)
- [ ] PDF export for other reports (sales-by-channel, inventory health) —
      reuse the reportlab layout helpers
- [ ] AI catalog import: auto-link a supplier from the document itself
      (vendor name extraction) so the user doesn't have to pick one
- [ ] AI catalog import: per-row confidence chips in the review table

## Verification Plan

- [x] Backend: `docker compose -f docker-compose.test.yml exec backend python -m pytest`
       — backend 367 passed / 8 skipped at last check (was 345 baseline)
- [x] Frontend: `npx ng test --watch=false` — 423 passed / 14 skipped
- [x] Manual walkthrough: CSV upload + approve + duplicate-SKU rerun, all
      verified live in the browser. AI-on / AI-off banner states verified
      against live capabilities endpoint. PDF download from low-stock
      widget verified (`fulcrum-low-stock-YYYY-MM-DD.pdf` blob download).
