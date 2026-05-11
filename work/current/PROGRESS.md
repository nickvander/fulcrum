# Progress Log

**Status:** Onboarding checklist and correction flow implemented **Current Phase:** Phase 7 -
Operational Reliability & Growth

## Current Work

- [84-customer-onboarding-readiness.md](./84-customer-onboarding-readiness.md)

## Important Product Decision

- PO receiving updates Fulcrum internal inventory only. Do not trigger
  MercadoLibre/Amazon stock sync from receiving; marketplace quantities must be
  allocated later in a separate channel-planning workflow.

## Next Session Starting Point

- Add optional demo workspace/sample data creation for trial customers.
- Add supplier document import review queue before PO/stock writes.
- Add launch readiness report for setup health, unresolved imports, test data,
  stock health, and marketplace credential status.
- Keep old quick wins in `work/future/`; they are useful later but secondary to
  onboarding customers safely.

## Recent Archive

- [83-platform-improvements-roadmap.md](../archive/83-platform-improvements-roadmap.md) -
  Supplier alias learning, review/undo, live dummy PO transaction, and
  marketplace allocation guardrails
- [82-po-receiving-to-inventory-workflow.md](../archive/82-po-receiving-to-inventory-workflow.md) -
  PO document parsing, invoice matching, and exact inventory receiving workflow
- [81-mercadolibre-deep-integration.md](../archive/81-mercadolibre-deep-integration.md) -
  Deep ML Sync & UI Polish
- [79-marketplace-integration-log.md](../archive/79-marketplace-integration-log.md) -
  AI Listing Generation
