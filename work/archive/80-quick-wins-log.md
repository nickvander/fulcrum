# 80: Quick Wins & AI Catalog Import - Progress Log

## Session 1 - 2026-01-24

### Completed

- Created plan file with scope and technical approach.
- Identified three main features: Low Stock Dashboard Widget, Export
  Service (CSV/PDF), AI Catalog Import.

### Next steps

- Get user feedback on open questions
- Begin implementation with Low Stock Widget

## Session 2 - 2026-05-17

### Completed since session 1

- **Low Stock Widget** — full implementation across three commits:
  - `ecff79c` initial widget + `/reports/low-stock` endpoint with
    threshold precedence and suggested-qty fallback.
  - `ef6e90b` made `reorder_point` / `reorder_quantity` editable on
    the product form (previously API-only).
  - `69f2c11` shopping-cart-style bulk reorder: multi-select on the
    widget, `POST /reports/low-stock/reorder` groups selected
    products by primary supplier and creates one DRAFT PO each.
- **Export Service — CSV first slice** (this session):
  - `GET /api/v1/reports/low-stock/export` streams CSV via
    `StreamingResponse`. Default limit 500 (cap 5000), date-stamped
    filename `fulcrum-low-stock-YYYY-MM-DD.csv`.
  - Frontend `LowStockService.exportLowStockCsv()` + "Export CSV"
    button on the widget header. Uses an `<a download>` blob trigger
    so the dashboard stays in view.
  - 2 new round-trip tests verify header row + per-row data + empty-
    list case + date-stamped filename + empty-string serialization for
    unset optional columns (not the literal "None").
  - 2 new i18n keys (`dashboard.lowStock.exportCsv`,
    `dashboard.lowStock.exportCsvTooltip`).

### Still open

- **PDF export** — needs a library choice (reportlab pure-Python vs.
  weasyprint with system font deps vs. external service). CSV covers
  the most common "give it to my accountant" use case so PDF is a
  polish follow-up.
- **AI Catalog Import** — entirely greenfield. Pattern would mirror
  the existing supplier-document import-review flow in
  `purchase_orders.py` but produce new Products instead of a PO.
- **Other reports' exports** — same `StreamingResponse + csv.writer`
  pattern can extend to sales-by-channel, inventory health, etc., as
  the need arises.

### Verification this session

- Backend full suite: 347/0/6 (+2 from baseline 345).
- Frontend: 413/0/14 (no regressions).
- Production build clean.
- i18n parity: 1171 keys.
- Pre-commit + pre-push hooks green.

## Session 3 - 2026-05-17 (continuation)

### AI Catalog Import — CSV slice

Picked up after a parallel-session pause that had only landed
`backend/src/models/catalog_import.py`. Verified main was clean at
`fa64707` and nothing else from the parallel session had been written.

Shipped two commits:

- `8fbb37c` — backend: `CatalogImport` model + alembic migration
  `e2f1a9b73c40`, `CatalogIngestionService` (CSV/TSV, EN + es-MX
  header aliases, `;` delimiter + European decimal-comma tolerance,
  5000-row cap), `/api/v1/catalog-imports/reviews{,/{id},/approve,
  /reject}` endpoints, 11 new tests. Backend suite now **359 passed,
  8 skipped**.

- `7979156` — frontend: `CatalogImportService`,
  `CatalogImportDialogComponent` (3-step: upload → editable review
  table → done with skipped-reasons), Products page "Import Catalog"
  button, en + es-MX i18n, 8 new specs. Frontend suite now **421
  passed, 14 skipped**.

Approval re-uses the existing `crud_product.create` path so SKU
validation, barcode/QR generation, and embedding queueing all fire
identically to manual product creation. Duplicate-SKU rows are skipped
with a reason instead of failing the whole batch, so the user can
edit + retry without losing progress.

### Still open

- PDF parser inside `catalog_ingestion_service.py` — no frontend
  changes required; the review/approve flow already accepts the
  `ExtractedCatalogItem` shape.
- PDF export for reports (still deferred).

## Session 4 - 2026-05-17 (closing)

Wrapped up every open acceptance criterion in the plan.

### Shipped

- `cc9b038` — **AI catalog import (PDF + image), gated on a configured
  API key.** Reuses the existing `InvoiceParserAgent` multimodal
  pipeline with a new `catalog_extraction.md` prompt. A new
  `ADKManager.is_ready()` predicate (ai_enabled AND active provider
  keyed) is exposed through `GET /api/v1/catalog-imports/capabilities`.
  The dialog renders a green "AI is configured" banner when ready or a
  yellow "needs AI" banner with an "Open Settings" link when not, and
  switches the file input's `accept` list accordingly. Backend
  endpoint returns 400 `aiRequiredForFileType` when a PDF lands
  without AI ready, 502 `aiExtractionFailed` when the provider errors.
  6 new backend tests + 2 new frontend specs.

- `4c7c5b7` — **PDF export for the low-stock report.** reportlab
  (pure Python, no system fonts) renders a landscape letter with
  severity-colored rows next to the existing CSV export. Same data,
  limits, and filename convention. New "Export PDF" button next to
  "Export CSV" in the widget header; both go through a shared
  `downloadBlob()` helper so the JWT stays in the Authorization header.
  2 new backend tests.

- Same commit as the AI slice also moved the supplier selector to the
  review step (so a forgotten upload-step selection isn't lost) and
  added `step="0.01" min="0"` to price/cost inputs.

### Verified live in the browser

- AI-off path: dialog shows the yellow banner with "Open Settings"
  link; `accept` is `.csv,.tsv,.txt`. API rejects `.pdf` with the
  localized 400 code.
- AI-on path (after seeding `ai_enabled=1` + a key in store_settings):
  banner switches to green "AI is configured"; `accept` grows to
  include `.pdf,.png,.jpg,.jpeg,.avif,.webp`.
- Low-stock widget: "Export PDF" button clicks initiate a real blob
  download of `fulcrum-low-stock-YYYY-MM-DD.pdf` (size sanity-checked
  against an authenticated curl).

### Final test counts

- Backend: 367 passed, 8 skipped (was 359 at end of Session 3 — +6
  AI gating, +2 PDF export).
- Frontend: 423 passed, 14 skipped (+2 dialog specs for AI gating).
- All pre-commit + pre-push hooks green; i18n parity validated; no
  regressions in unrelated suites.

### Closed

All acceptance criteria in `80-quick-wins-plan.md` are now ticked.
Future enhancements (other reports' PDF exports, vendor auto-link from
AI extraction, per-row confidence chips) moved to the plan's "Future
Enhancements" section to be opened as separate initiatives.
