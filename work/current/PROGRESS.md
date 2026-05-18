# Progress Log

**Status:** Reports surface + supplier import polish + product-form tests all
green on `main`. No active in-flight slice.
**Current Phase:** Phase 7 — Customer Onboarding Reliability + Day-to-Day
Operator Tools.

## Current Work

_(nothing in flight — see `work/future/` for the next strategic
candidates, or pick from "Suggested Next Slices" below.)_

## Important Product Decisions

- PO receiving updates Fulcrum internal inventory only. Do not trigger
  MercadoLibre/Amazon stock sync from receiving; marketplace quantities must
  be allocated later in a separate channel-planning workflow.
- Mexico is the primary market; MercadoLibre Full is the primary fulfillment
  path. FBM / direct storefront are future-only.
- Work happens on `main` directly; scratch `claude/*` branches get rebased
  onto `main`. No PR workflow.

## Most Recent Shipped (last ~10 commits)

- `f8f8b61` Mark product-form specs backlog item done.
- `afb760f` Unblock the 5 skipped product-form specs (frontend 450/0
  skipped, was 432/14 skipped). Root causes were mostly infrastructure
  (TranslocoTestingModule, stale httpMock.expectOne calls, missing mock
  methods, setValue→patchValue); the dead ProductsComponent was deleted.
- `97c5f40` Inventory adjustment audit log UI page (/products/audit) +
  paginated JSON list endpoint.
- `ed546a7` Named CSV import templates ("Map & Template" UX) — model +
  migration, CRUD + preview endpoint, mapping sub-dialog, template
  dropdown on the catalog import dialog.
- `f6cca64` CSV+PDF exports for PO, sales orders, expenses, and the
  inventory adjustment audit log (all on the shared report_export module
  shipped in 1cf3e14).
- `1cf3e14` Reusable report_export module (ReportColumn / ReportTable /
  stream_csv / stream_pdf) + sales-by-channel + inventory-snapshot
  reports. Low-stock refactored onto the same module.
- `cc9b038` AI catalog import (PDF + image), gated on configured API key.
  ADKManager.is_ready() + GET /catalog-imports/capabilities.
- `10e862b` AI vendor auto-link: catalog AI agent extracts the document
  vendor name; endpoint fuzzy-matches to an existing supplier and
  pre-links the review.
- `9dfacd0` Supplier import queue: multi-select bulk-reject + search +
  supplier filter UI.
- `4c7c5b7` Low-stock PDF export (reportlab, severity-colored rows).
- `8fbb37c` AI catalog import: CSV slice (`/api/v1/catalog-imports/...`
  endpoints + dialog).

## Suggested Next Slices

Pick one of these (or anything from `work/future/`):

- **AmazonAdapter SP-API completion** — `fetch_all_listings` shipped in
  `7b251fe`; `sync_inventory` and `fetch_orders` are still stubbed. The
  ML connector is the reference implementation.
- **Stockout / velocity / margin reports** — `endpoints/reports.py`
  currently only exposes low-stock. The `report_export` helper makes
  each new report ~25 lines + a SQL query.
- **Alerting on low margin / sudden sales dips / out-of-stock risk** —
  Track 3 Step 6 of `80-advanced-analytics.md`. Could ship one channel
  (email via SMTP) first.
- **Marketplace channel cards: surface ML / Amazon sync state** — today
  the reauth chip is only on the stock-transfer sync panel; the
  channel-list cards still ignore it.
- **Mercado Pago Checkout API integration** — research lives in
  `work/future/mercadopago-checkout-research.md`. Greenfield, sizable.
- **Rust backend migration first slice** — plan in
  `work/future/81-rust-backend-migration-plan.md`. Highest-impact
  candidate is product listing.

## Verification Surface

- Backend full suite: `docker compose -f docker-compose.test.yml run --rm
  backend python -m pytest -q --ignore=tests/integration/test_mercadolibre_live.py`
  → 410 passed, 8 skipped at last green.
- Frontend full suite: `npx ng test --watch=false` → 450 passed, 0
  skipped at last green.
- Pre-commit + pre-push hooks: linter + fast backend tests + i18n parity.

## Recent Archive

- [00-backlog-may-2026.md](../archive/00-backlog-may-2026.md) — Both
  frontend testing items (user-bulk-import + product-form specs)
  shipped.
- [87-sales-orders-cherry-handoff.md](../archive/87-sales-orders-cherry-handoff.md) —
  All 7 commits landed on main.
- [usability-roadmap.md](../archive/usability-roadmap.md) — Items 1–4
  (low-stock dashboard, reorder workflow, marketplace integration,
  supplier catalog import) all shipped. Item 5 (more marketplaces)
  rolls into the standalone Amazon / future-marketplace candidates.
- [ai-invoice-processing.md](../archive/ai-invoice-processing.md) —
  Supplier-document import-review + AI catalog parsing shipped.
- [80-quick-wins-{plan,log}.md](../archive/) — Low Stock Widget,
  Export Service, AI Catalog Import (CSV + PDF), supplier auto-link.
- [86-marketplace-allocation-workflow.md](../archive/86-marketplace-allocation-workflow.md) —
  Stock-transfer model + ML Full API integration + allocation planner.
- [84-customer-onboarding-readiness.md](../archive/84-customer-onboarding-readiness.md) —
  Launch readiness report + supplier import review queue.
