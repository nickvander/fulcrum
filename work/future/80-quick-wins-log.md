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
