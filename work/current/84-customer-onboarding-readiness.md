# 84: Customer Onboarding Readiness

## Goal

Make Fulcrum ready for real customer onboarding by smoothing the first-run
experience, protecting core inventory workflows, and making setup status obvious.
The next session should prioritize features that help a new customer get from
empty account to usable inventory operations without support hand-holding.

## Current Baseline

- Backend and frontend were launched locally after the supplier alias work.
- Dummy API transaction passed:
  - created supplier
  - created product
  - created purchase order with Alibaba SKU/name
  - learned supplier alias
  - received quantity into internal inventory
  - verified product stock increased
  - verified alias undo removes the active mapping
- Browser smoke passed:
  - login
  - purchase order import dialog
  - supplier detail Products tab shows learned alias chip
- Latest pushed commits:
  - `96a59b0` Learn supplier product aliases from confirmed POs
  - `1214757` Show learned aliases on supplier detail products

## Product Guardrails

- PO receiving updates Fulcrum internal inventory only.
- Do not automatically push received stock to Amazon or MercadoLibre.
- Marketplace quantities require a separate allocation/planning workflow.
- Customer-facing onboarding should guide, validate, and preview before writing
  inventory, marketplace, or cost-affecting data.

## Best Next Feature: Onboarding Checklist and Setup Health

Build a lightweight onboarding command center that tells a new customer exactly
what is configured, what is missing, and what action to take next.

### Why This Is First

Customers need confidence before they import supplier documents or connect
marketplaces. A checklist makes the product feel coherent and reduces support
questions by turning scattered setup steps into a visible path.

### First Slice

1. Backend setup-health endpoint
   - Add `/api/v1/onboarding/status`.
   - Return setup state for:
     - admin/user profile exists
     - store settings configured
     - at least one product exists
     - at least one supplier exists
     - at least one supplier-product mapping or learned alias exists
     - at least one PO exists
     - at least one inventory movement exists
     - marketplace credentials configured, but not required
   - Include `complete`, `warning`, `action_label`, and `route` per step.

2. Frontend onboarding panel
   - Add a dashboard or Settings panel with actionable checklist rows.
   - Use existing routes:
     - Products
     - Suppliers
     - Purchase Orders
     - Marketplace settings
   - Show clear states: Done, Needs attention, Optional.
   - Keep it operational, not a marketing landing page.

3. Empty-state improvements
   - Product list: direct action to create/import product.
   - Supplier list: direct action to add supplier or import supplier document.
   - PO list: direct action to create/import PO.
   - Supplier detail Products tab: explain no supplier-products only when empty.

4. Verification
   - Backend tests for setup-health combinations.
   - Frontend component test for checklist states.
   - Browser smoke:
     - login
     - dashboard/checklist visible
     - create or detect existing setup steps
     - navigate from checklist action to target route

## Next Best Features After Checklist

1. Sample data or guided demo mode
   - Add an explicit "Create demo workspace" action for trial customers.
   - Seed a sample supplier, product, PO, and stock movement.
   - Must be clearly reversible or marked as demo data.

2. Import review queue
   - Queue imported supplier PDFs/images before they become POs or stock.
   - Show match confidence, learned aliases, proposed product/variant, and
     discrepancy warnings.
   - Keep direct PO creation working.

3. Receiving correction flow
   - Add a correction/reversal action for receiving mistakes.
   - Preserve stock movement audit history instead of silently editing received
     quantities.

4. Marketplace connection health
   - Show credential state, last sync attempt, missing scopes, and errors.
   - Keep inventory allocation separate from raw stock receiving.

5. Launch readiness report
   - One page that summarizes products, suppliers, stock, POs, credentials,
     unresolved import matches, and test/dummy data warnings.

## Definition of Done for the Next Session

- New onboarding status endpoint is tested.
- New frontend checklist is visible after login or from Settings/Dashboard.
- Checklist actions route to real screens.
- Existing PO receiving and supplier alias tests still pass.
- Browser smoke confirms a new customer can see what to do next.
- Update this file with completed work and move it to `work/archive/` when done.

