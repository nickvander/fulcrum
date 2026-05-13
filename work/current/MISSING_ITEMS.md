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
- [x] OAuth token refresh handling improvements
      - Implemented in `87-marketplace-oauth-hardening.md`.
      - 5-minute pre-refresh buffer, typed `ReauthorizationRequiredError`,
        `needs_reauthorization` + `last_refresh_error` on the credential row,
        and a clear reauth banner in the stock-transfer sync panel.
      - Open follow-up: surface the reauth state on the marketplace cards
        (today only the sync panel shows it) and wire
        `force_refresh_access_token` into a 401-retry decorator.

## Future

- [ ] Enhance Marketplace Status UI with sync indicators (the
      `needs_reauthorization` flag is now available on the credential
      and surfaces in the stock-transfer sync panel — extend that to
      the Marketplaces channel cards too).
- [ ] Reorder workflow (shopping-cart style): pick low-stock products
      across the dashboard, group by supplier, create one draft PO per
      supplier in a single pass. Natural follow-on to the new
      low-stock dashboard widget (`88-low-stock-dashboard-widget.md`).
