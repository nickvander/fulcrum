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

1. Demo-data cleanup guardrail
   - Show customers which demo records exist before go-live.
   - Provide a guided cleanup path that does not delete real customer records.

2. Import review match assistance
   - From an unmatched supplier line, create a Fulcrum product or supplier alias
     without leaving the review dialog.
   - Make the review queue usable when a customer imports their first messy
     Alibaba document.

3. Import review history
   - Add filters for pending, approved, and rejected reviews.
   - Keep approved/rejected documents auditable without cluttering the active
     queue.

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
