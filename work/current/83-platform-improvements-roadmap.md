# 83: Platform Improvements Roadmap

## Goal

Improve Fulcrum with additive, reviewable features that make inventory,
marketplace, supplier, and operations workflows safer without breaking existing
purchase order receiving, product inventory, or marketplace behavior.

## Guardrails

- Preserve current PO receiving behavior: receiving updates internal inventory
  only.
- Do not automatically sync received stock to Amazon or MercadoLibre.
- Add new workflows behind explicit user actions, preview screens, or feature
  flags when they affect inventory, marketplace listings, or costs.
- Prefer audit trails and reversible actions for stock, cost, and channel
  availability changes.
- Keep existing API contracts compatible unless there is a migration plan and
  test coverage.

## Best Next Improvements

1. Supplier document review queue
   - Add a queue for imported Alibaba/PDF/image documents that need human
     confirmation before stock movement.
   - Show extracted item, matched product/variant, confidence, proposed receive
     quantity, remaining PO quantity, and discrepancy warnings.
   - Keep the existing direct receive dialog working.

2. Supplier alias learning
   - Store approved mappings like "Alibaba item name/SKU -> Fulcrum
     product/variant."
   - Use mappings to improve future PO/invoice matching.
   - Add review and undo so bad mappings do not poison future imports.

3. Marketplace allocation planning
   - Create a separate workflow that decides how much internal inventory is
     allocated to each marketplace/listing.
   - Show internal on-hand, reserved, allocated, and unallocated quantities.
   - Sync only approved marketplace allocations, not raw warehouse stock.

4. Inventory adjustment safety
   - Add clearer stock movement history by source: PO receive, manual
     adjustment, bundle assembly, marketplace order, and correction.
   - Add reversal/correction flows for receiving mistakes instead of editing
     received quantities silently.

5. Operational dashboards
   - Low-stock and stockout-risk dashboard based on sales velocity and reorder
     lead time.
   - Supplier receiving aging: ordered, partially received, overdue, and
     mismatched documents.
   - Marketplace listing health: disconnected credentials, stale listing data,
     and sync errors.

6. Export and audit reporting
   - CSV exports for inventory valuation, stock movement history, PO receiving,
     supplier performance, and marketplace allocations.
   - Keep PDF exports secondary until CSV workflows are reliable.

## Suggested Order

1. Build supplier alias learning because it improves every future import.
2. Add receiving correction/audit improvements to protect stock accuracy.
3. Build marketplace allocation planning as a separate channel workflow.
4. Add dashboards and exports once the underlying states are reliable.

## Verification Standard

- Backend focused tests for each changed workflow.
- Frontend component tests for review/allocation forms.
- Browser smoke for the primary user path when UI changes.
- No feature should change existing PO receiving or marketplace sync behavior
  unless the change is explicitly part of that task.
