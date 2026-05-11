# Progress Log

**Status:** Launch readiness and supplier import review queue implemented **Current Phase:** Phase 7 -
Customer Onboarding Reliability

## Current Work

- [85-customer-onboarding-next.md](./85-customer-onboarding-next.md)

## Important Product Decision

- PO receiving updates Fulcrum internal inventory only. Do not trigger
  MercadoLibre/Amazon stock sync from receiving; marketplace quantities must be
  allocated later in a separate channel-planning workflow.

## Next Session Starting Point

- Add demo-data cleanup warning/path before customers go live.
- Add one-click product/supplier alias creation for unmatched supplier import
  lines.
- Add import review history filters for approved/rejected documents.
- Start marketplace allocation planning as a separate workflow from receiving.
- Keep old quick wins in `work/future/`; they are useful later but secondary to
  onboarding customers safely.

## Recent Archive

- [84-customer-onboarding-readiness.md](../archive/84-customer-onboarding-readiness.md) -
  Launch readiness report, supplier import review queue, Alibaba sample import,
  and draft PO approval smoke
- [83-platform-improvements-roadmap.md](../archive/83-platform-improvements-roadmap.md) -
  Supplier alias learning, review/undo, live dummy PO transaction, and
  marketplace allocation guardrails
- [82-po-receiving-to-inventory-workflow.md](../archive/82-po-receiving-to-inventory-workflow.md) -
  PO document parsing, invoice matching, and exact inventory receiving workflow
- [81-mercadolibre-deep-integration.md](../archive/81-mercadolibre-deep-integration.md) -
  Deep ML Sync & UI Polish
- [79-marketplace-integration-log.md](../archive/79-marketplace-integration-log.md) -
  AI Listing Generation
