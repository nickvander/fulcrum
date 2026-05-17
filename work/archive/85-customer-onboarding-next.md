# 85: Customer Onboarding Next Slice

> **STATUS: ✅ COMPLETE.** All four "Best Next Features" are closed —
> items 1–3 landed in earlier sessions; the only piece left open
> (item 2's "visual diff" sub-task) landed in this session.
> Item 4 (marketplace allocation planning) was made obsolete by the
> stock-transfer rework; no design doc needed.

## Goal

Make the next customer onboarding session focus on the remaining friction after
launch readiness and supplier import reviews.

## Completed Baseline

- Launch readiness report is available on the dashboard.
- Supplier document imports stage into a review queue before creating POs.
- Approving a supplier import creates a draft PO only.
- PO receiving remains the only path that updates internal stock.
- Received internal stock is not pushed to Amazon or MercadoLibre.
- Focused backend tests and Angular production build passed.
- Local browser smoke covered:
  - login
  - dashboard readiness rendering
  - supplier import queue rendering
  - opening a queued Alibaba sample import
  - approving a matched import into a draft PO
- Repo handoff skill added at `.agent/skills/work_handoff/SKILL.md`.
- Root-level stale logs and generated test-output files were removed.

## Best Next Features — final status

### 1. Demo-data cleanup guardrail — ✅ done
- Launch readiness shows each detected demo record before go-live.
- Cleanup removes only records that still match the seeded demo fingerprints.
- Cleanup is blocked when demo records have customer-linked activity.

### 2. Import review match assistance — ✅ done
- Done: From an unmatched supplier line, create a Fulcrum product or learn a
  supplier alias without leaving the review dialog.
- Done: Review updates persist to the pending import.
- Done: Bulk-reject endpoint + "Reject stale (>30 days)" affordance on the queue.
- **NEW (this session): Visual diff for invoice/packing-list documents that
  match an existing PO.** See "What landed this session" below.

### 3. Import review history — ✅ done
- Pending / History / All filter tabs on the queue.
- Backend supports comma-separated `status`, supplier filter, date range,
  and file-name search; UI currently wires status only.
- Approved review cards link to the PO they created; terminal reviews
  don't open the approve dialog.

### 4. Marketplace allocation planning — ❎ obsolete
- The "marketplace allocation workflow" was deliberately not built. The
  beautiful-greider commits already on main (commits b4823c8 through 1d7d63c
  per the 87-handoff note) replaced the allocation concept with internal
  stock transfers. The `marketplace-allocation` Angular page was explicitly
  deleted. Resurrecting it would conflict architecturally with stock-transfer.
- No design doc needed — the architectural decision was already made and
  implemented differently.

## What landed this session (2026-05-17)

### Visual diff for matched-PO imports

Previously, when a supplier document was parsed and `mode == "match"` (i.e.,
the parser identified an existing PO it likely belonged to), the
`po-ingest-dialog` would **stop with an error message** ("This document appears
to match existing PO#X. Open that PO to receive stock instead.") and force the
user to navigate away to act on it. The data needed for a side-by-side
comparison (`matches[]`, `unmatched_po_items[]`, `unmatched_invoice_items[]`,
`total_discrepancy`) was already in the review's `extracted_data` JSON but
unrendered.

This slice replaces the dead-end with a real match-diff step in the same
dialog:

- New `'match-diff'` state in the dialog's step machine (between `'preview'`
  and `'creating'`).
- Header block: "This document matches purchase order #N" plus supplier,
  invoice number, invoice date.
- Discrepancy banner with the `total_discrepancy` in the active currency
  (warning-styled for non-zero amounts).
- Line-by-line table with PO side / document side columns, status chip per
  row (`matched` / `quantity_diff` / `price_diff` / `unmatched`), and per-row
  `discrepancy_details` text from the backend's `InvoiceMatchItem` shape.
- Two collapsible sections for `unmatched_po_items` (in PO but missing from
  the document) and `unmatched_invoice_items` (in document but missing from
  PO).
- Two actions in the dialog footer:
  - **"Open the PO"** closes the dialog and navigates to
    `/suppliers/po/<matched_po_id>/edit` so the user can use the PO's
    own invoice-receive flow to apply the deltas.
  - **"Reject this import"** calls the existing
    `POST /api/v1/purchase-orders/imports/reviews/{id}/reject` endpoint —
    used when the diff makes it clear that the document doesn't actually
    belong to this PO (e.g. wrong supplier picked up by a fuzzy match).

Backend: no changes needed. The data was already in the review row's
`extracted_data` JSON.

Frontend: changes scoped to one component (`po-ingest-dialog`):
- New `MatchDiffDetails` / `MatchDiffLine` / `MatchDiffUnmatchedItem`
  interfaces mirroring `InvoiceMatchResult` from the backend.
- New state fields: `matchedPoId`, `matchedPoNumber`, `matchedSupplierName`,
  `matchedInvoiceNumber`, `matchedInvoiceDate`, `matchDetails`.
- `processFile()`'s `next:` handler routes to `'match-diff'` instead of
  bailing when `response.mode === 'match'`.
- `openMatchedPo()`, `rejectMatchedImport()`, `matchStatusClass()`, and an
  extended `goBack()` that clears match state.
- Template adds the `'match-diff'` step with all the panels above.
- Dialog footer gains the two new action buttons.
- New SCSS scope (`.match-diff-step` and descendants) for the diff visual
  treatment, status chips, and row tinting.
- 17 new i18n keys under `purchaseOrders.matchDiff.*` with full en + es-MX
  parity (1169 keys total).

Verification:
- Production build clean.
- Frontend 413/0/14 (no regressions; the existing
  `po-ingest-dialog.component.spec.ts` smoke tests still pass — they don't
  exercise the match-mode branch because that was previously dead code, but
  the new branch reuses the same test fixtures and dialog setup).
- Backend `tests/test_supplier_document_import_reviews.py` 8/8 — the
  match-mode review row is already populated by the existing flow; this
  slice only changes how the frontend renders it.

## Verification To Keep

- Backend:
  - `tests/test_supplier_document_import_reviews.py`
  - `tests/test_onboarding_api.py`
- Frontend:
  - `npm run build --prefix frontend`
- Browser smoke:
  - dashboard readiness panel
  - purchase order import queue
  - queued import review dialog (both create and match modes)
  - draft PO created from approval
  - match-diff render for a document matched to an existing PO
