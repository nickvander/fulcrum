# Progress Log

**Status:** Ready for customer onboarding sprint **Current Phase:** Phase 7 -
Operational Reliability & Growth

## Current Work

- [84-customer-onboarding-readiness.md](./84-customer-onboarding-readiness.md)

## Important Product Decision

- PO receiving updates Fulcrum internal inventory only. Do not trigger
  MercadoLibre/Amazon stock sync from receiving; marketplace quantities must be
  allocated later in a separate channel-planning workflow.

## Next Session Starting Point

- Build the onboarding checklist/setup-health workflow first.
- Start with a backend `/api/v1/onboarding/status` endpoint, then add a
  dashboard or settings panel that routes users to Products, Suppliers,
  Purchase Orders, and Marketplace Settings.
- Keep old quick wins in `work/future/`; they are useful later but not the
  cleanest next step for onboarding customers.

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
