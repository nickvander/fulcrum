# 85: Customer Onboarding Next Slice

## Goal

Make the next customer onboarding session focus on the remaining friction after
launch readiness and supplier import reviews.

## Completed Baseline

- Launch readiness report is available on the dashboard.
- Supplier document imports now stage into a review queue before creating POs.
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
  - Note: `.agents/` is mounted read-only in this workspace, while the repo's
    checked-in skills are under `.agent/skills/`.
- Root-level stale logs and generated test-output files were removed.

## Best Next Features

1. Demo-data cleanup guardrail - done
   - Launch readiness shows each detected demo record before go-live.
   - Cleanup removes only records that still match the seeded demo fingerprints.
   - Cleanup is blocked when demo records have customer-linked activity.

2. Import review match assistance
   - Done: From an unmatched supplier line, create a Fulcrum product or learn a
     supplier alias without leaving the review dialog.
   - Done: Review updates persist to the pending import so reopening the dialog
     keeps the match.
   - Done: Bulk-reject endpoint + "Reject stale (>30 days)" affordance on the
     queue. Accepts explicit `review_ids` for future multi-select UI.
   - Remaining: Visual diff for invoice/packing-list documents that match an
     existing PO (qty/price deltas side-by-side).

3. Import review history - done
   - Pending / History / All filter tabs on the queue.
   - Backend supports comma-separated `status`, supplier filter, date range,
     and file-name search; UI currently wires status only.
   - Approved review cards link to the PO they created; terminal reviews
     don't open the approve dialog.

4. Marketplace allocation planning
   - Design the separate workflow that decides how much internal inventory is
     allocated to MercadoLibre or Amazon.
   - Do not connect PO receiving directly to marketplace stock sync.

## Verification To Keep

- Backend:
  - `tests/test_supplier_document_import_reviews.py`
  - `tests/test_onboarding_api.py`
- Frontend:
  - `npm run build --prefix frontend`
- Browser smoke:
  - dashboard readiness panel
  - purchase order import queue
  - queued import review dialog
  - draft PO created from approval
