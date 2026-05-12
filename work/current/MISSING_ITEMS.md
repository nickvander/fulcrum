# Missing Items Tracker

## High Priority

- [x] Customer onboarding checklist/setup-health workflow
      - Show store, products, suppliers, PO, inventory movement, supplier alias,
        and marketplace credential readiness.
      - Provide direct actions to complete missing setup.
- [x] Customer-ready empty states for Products, Suppliers, Purchase Orders, and
      Supplier detail Products tab.
- [x] Receiving correction/reversal flow so onboarding users can fix stock
      mistakes without editing history silently.
- [x] Optional demo workspace/sample data for trial onboarding.
- [x] Launch readiness report for setup health, unresolved imports, test data,
      stock health, and marketplace credential status.
- [x] Demo-data cleanup warning/path before customer go-live.
      - Lists exact demo records in launch readiness.
      - Cleans only records that still match demo fingerprints.
      - Blocks cleanup when demo records have customer-linked activity.

## Medium Priority

- [x] Supplier document review queue for imported Alibaba PDFs/images before PO
      or stock updates.
- [ ] Supplier import review polish:
      - bulk reject/cleanup stale reviews
      - [x] one-click create product / learn supplier alias from unmatched import
        lines
      - visual diff for uploaded invoice/packing-list documents that match an
        existing PO
- [x] Marketplace allocation workflow before stock sync. Do not sync received
      internal stock directly to Amazon/MercadoLibre.
      - Implemented in `86-marketplace-allocation-workflow.md` (Slices 1-3).
      - Stock-transfer model + allocation planner replace any implicit sync
        from PO receiving.
- [x] Sync approved listing/inventory allocations to actual marketplace APIs
      (Amazon SP-API, MercadoLibre API)
      - MercadoLibre Full inbound shipment + listing-quantity sync wired up
        in Slice 2 with a stub fallback. First live token will exercise the
        real API path.
- [ ] OAuth token refresh handling improvements

## Future

- [ ] Enhance Marketplace Status UI with sync indicators
