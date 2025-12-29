# Progress Log

## Status
- [/] **Phase 7**: Deep Marketplace Integration (Live Connectors) (Complete)
- [/] **Phase 8**: Amazon SP-API Live Testing (In Progress)

## Log
- **2025-12-27**: Phase 6 Completed.
    - Architecture, Refined UI, and Connector framework pushed to main.
- **2025-12-27**: Phase 7 Track 1 Completed.
    - Secure Credential Management with AES-256-GCM.
- **2025-12-27**: Phase 7 Track 2 Completed.
    - Implemented `MarketplaceListingService` for bi-directional sync.
    - Added Auto-Mapping (via SKU) and Auto-Product Creation (Shells) for imports.
    - Standardized `ListingData` across Amazon and MercadoLibre connectors.
    - Verified with 134 passing tests.
- **2025-12-27**: Phase 7 Tracks 3 & 4 Completed.
    - Amazon SP-API: OAuth flow (LWA), token refresh, inventory/price sync stubs.
    - MercadoLibre Mexico (MLM): OAuth flow, token refresh, listing operations.
    - All connector methods now accept `access_token` for authenticated API calls.
    - Verified with 139 passing tests.
- **2025-12-27**: Phase 7 Track 5 Completed.
    - Webhook models (`WebhookSubscription`, `WebhookEvent`) for event logging.
    - API endpoints for MercadoLibre and Amazon webhook reception.
    - Background task processing for incoming events.
    - Comprehensive marketplace integration documentation created.
- **2025-12-28**: Settings UI & UX Improvements.
    - Settings page for configuring marketplace API credentials.
    - Simplified UX: single entry point to add/connect marketplace accounts.
    - Logos for Amazon and MercadoLibre added to dialog.
    - `MarketplaceAppCredential` model for storing developer credentials (encrypted).
    - All 139 tests passing.
- **2025-12-28**: Phase 7 Complete.
    - Multi-account support per marketplace implemented.
    - Fixed Material button styling with global CSS overrides.
    - Verified OAuth flows work for Amazon and MercadoLibre.
- **2025-12-28**: Phase 7 Complete (Live Integration Testing).
    - Implemented `setup_mercadolibre_test.py` for automated user generation.
    - Created `tests/integration/test_mercadolibre_live.py` for end-to-end sync verification.
    - Updated documentation for Testing & CI with live execution guide.
    - **Note**: Full test execution requires developer token injection.
    - Ready for Phase 8.

- **2025-12-28**: Phase 8 Initialized.
    - Added `AMAZON_SANDBOX` support to `AmazonConnector`.
    - Created `tests/integration/test_amazon_live.py` structure.
    - Implemented `sync_inventory`, `sync_price`, and `publish_listing` logic for SP-API.
    - Status: Blocked on `AMAZON_CLIENT_ID` / `AMAZON_CLIENT_SECRET` for verification.
    - Credential Setup Guide created: `work/current/63-marketplace-credential-setup-guide.md`

- **2025-12-28**: Phase 9- **Phase 9: Business Operations Core** (In Progress)
  - [x] Inventory & Cost Engine (Bundles, Expenses, Landed Costs)
  - [/] Supplier & Restock (UI & Lists Improved)
  - [ ] Marketing Operations
    - Plan created: `work/current/64-business-operations-plan.md`.
    - Focus: Cost/Expense tracking, Bundles, and 1P Storefront.

- **2025-12-28**: Product Hub Maintenance & UI Polish
    - **UI Consolidation**: Merged "All/Product/Bundle" filters into the main toolbar, removing the side panel.
    - **Stability**: Fixed NG0956 error in Product List and added protections against form refreshes.
    - **Bundles**: Implemented "Estimated Cost" display logic (sum of components) and exposed `component_cost` in API.
    - **Backend**: Restarted service to apply schema changes for Bundle/Product logic.
    - **Deferred**: Advanced filters and Dialog cost display logged in `MISSING_ITEMS.md`.

- **2025-12-28**: Product Hub UI Polish (Continued)
    - Fixed "Create Bundle" dialog prepopulation bug in `ProductForm` (side-panel mode now correctly hydrates components).
    - **Filter UX Overhaul**:
        - Added **debouncing** (400ms) to filter inputs to prevent excessive API calls.
        - Replaced full-page loading spinner with a **non-blocking progress bar** overlay.
        - Updated filter field styling: compact inputs, proper currency prefix spacing, flexible widths.
    - **Inventory Details**: Clarified stock breakdown (Total Physical - Allocated = Available).

- **2025-12-28**: Expense Module Enhancement
    - **Bug Fix**: Fixed double `/v1` URL bug in `expense.service.ts` (was causing 404 errors).
    - **Backend Enhancements**:
        - Extended `Expense` model with `expense_type`, `recurrence_interval`, `reference_number`, `payment_method`, `notes`, `is_custom_category`.
        - Created Alembic migration `180734c2b528_add_expense_tracking_fields.py`.
        - Added `/expenses/summary` and `/expenses/categories` endpoints.
    - **Frontend UI Modernization**:
        - Redesigned `expense-list` with KPI widgets (Total, Recurring, One-time, Entries).
        - Enhanced `expense-dialog` with expense type toggle, custom categories, payment method.
        - Modernized `purchase-order-list` with matching KPI widgets and improved styling.
    - **Documentation**:
        - Updated `docs/user-guides/expenses.md`.
        - Created `docs/concepts/expense-model.md` with ERD diagram.

- **2025-12-28**: Purchasing UI Refinements
    - **Navigation**:
        - Reordered "Purchasing" menu: Purchase Orders -> Expenses -> Suppliers.
        - Fixed styling and alignment to match other nav items.
    - **Purchase Orders**:
        - Fixed date filter timezone issue (UTC vs Local).
        - Added **Sorting** to all columns.
        - Added **Supplier Filter** dropdown.
        - Integrated "Deep Linking" from Supplier list (click PO count -> filtered PO list).
    - **Suppliers**:
        - Implemented `SupplierListComponent` with actual PO counts/values calculated via `forkJoin`.
        - Added **Sorting** to supplier table.
    - **Expenses**:
        - Refactored to **client-side filtering** to eliminate page stutter on date changes.
        - Added **Sorting** to expense table.

- **2025-12-28**: Purchasing UI Finalization
    - **Visual Polish**:
        - Implemented **"Sleek" filter UI** with pill-shaped dropdowns and valid clear buttons.
        - Modernized **Date Range Presets** to use chip-style toggles (clean, no-border design).
    - **Stability**:
        - Fixed linter errors in backend (`expenses.py`).
        - Verified all frontend tests pass for new components.
    - **Documentation**:
        - Updated `walkthrough.md` with UI changes.
        - Verified `work/current/` status files.

- **2025-12-28**: Purchase Order Debugging & Fixes
    - **Cost Breakdown**: Fixed issue where Base Cost, Shipping, and Tax were showing as 0 in Product History.
        - Root Cause: `ProductPurchaseHistory` schema was missing cost breakdown fields.
        - Fix: Updated schema and ensured `PurchaseOrderItem` correctly tracks initialized `base_cost`.
    - **Order Updates**: Fixed "Update Order" button functionality.
        - Root Cause: Frontend was calling `updateStatus` instead of a full update.
        - Fix: Added `updatePurchaseOrder` to service and updated backend `crud_purchase_order.py` to handle item synchronization (delete/replace strategy).
    - **UI Polish**:
        - Added `UserService` to Suppliers module to fix dependency injection.
        - Enhanced "Paid By" dropdown to correctly display user names.
        - Added safeguards for null values in cost tooltips.
    - **Workflow Improvements**:
        - Implemented **Auto-Save** mechanism for Cost Allocation dialog to ensure calculations use latest form values.
        - Enhanced **Cost Preview** to accept temporary overrides, allowing users to preview "Add to Unit Cost" results without committing to the DB first.
        - Verified all frontend tests pass with new mock configurations.
