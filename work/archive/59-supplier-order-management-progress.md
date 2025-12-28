# Progress Log

## Status

- [x] **Phase 5**: Supplier Order Management Complete (AI Invoice deferred)
- [x] **Phase 5.5**: Additional Features (Cost Allocation, Invoices, Multi-Source)
- [x] **Phase 5.6**: Safety & Polish (PO Deletion, Modern Receiving UI, Product Details)

## Log

- **2025-12-27**: Phase 5.5 - Additional Supplier Features.
    - **Cost Allocation Preview**:
        - Added `base_cost`, `shipping_allocated`, `taxes_allocated`, `other_allocated` fields to PO items.
        - Created `/costs/preview` and `/costs/apply` API endpoints.
        - Built `CostAllocationDialogComponent` for reviewing cost breakdown before applying.
    - **Invoice Management**:
        - Created `SupplierInvoice` schemas and CRUD.
        - Added secure file upload with type validation (PDF/PNG/JPG), size limits (10MB), UUID filenames.
        - Added invoice upload/list/delete endpoints to PO API.
    - **Multi-Source Products**:
        - Created `SupplierProduct` model for products with multiple suppliers.
        - Added fields: `supplier_sku`, `cost_price`, `is_primary`, `lead_time_days`.
        - Created CRUD with `get_by_product()`, `get_by_supplier()`, `set_as_primary()`.
        - Added full REST API at `/supplier-products`.
    - **UX Improvements**:
        - Renamed "Suppliers" nav to "Purchasing".
        - **Included Cost Allocation Exclusions**: Users can opt-out specific items from cost distribution.
        - **Better Draft Management**: Clear Draft/Cancel actions, and auto-creation of Backend Drafts for advanced features (Uploads, Cost Dialog).
        - **Visual Polish**: Real-time allocation hints in table, Invoice layout fixes.
    - **PO Deletion & Safety**:
        - Implemented `DELETE /purchase-orders/{id}` with strict safety check: blocks deletion if *any* items have been received (prevents orphaned inventory).
        - Added frontend "Delete Order" button with confirmation for Draft/Ordered POs.
    - **Visual Overhauls**:
        - **Receiving Dialog**: Redesigned with modern Card Grid layout, larger images, and clearer "Ordered vs Received" stats.
        - **Product List**: Added "Cost Price" to Grid View.
        - **Interaction**: Row click now opens "Read-Only Details" dialog; Edit is a deliberate secondary action.
        - **Navigation**: Added "Return to PO" link in Product purchase history.
    - **Safety**:
        - **PO Locking**: Implemented Read-Only mode for non-Draft orders (Ordered/Received) to prevent accidental data corruption. Added "Unlock to Edit" workflow with confirmation.
        - **Data Freshness**: Product Details dialog now explicitly fetches fresh data, ensuring Real-time Cost/Inventory accuracy.

- **2025-12-28**:
    - **Goal**: Final Polish & Release (Phase 5.10)
    - **Status**: Completed
    - **Notes**:
        - Fixed Product Detail Dialog image visibility (path resolution + CSS).
        - Implemented Purchase Order Locking (safety mechanism for non-draft POs).
        - Fixed Backend `NameError` in receiving logic.
        - Resolved `403` error in audit logs (strict superuser check).
        - Fixed Frontend Test Mocks (`ActivatedRoute` params, `MatDialog`).
        - Updated Documentation (`supplier-management.md`, `MISSING_ITEMS.md`).

- **2025-12-27**: Completed Phase 5 - Supplier Order Management.
    - **Backend**:
        - Implemented `PurchaseOrder`, `PurchaseOrderItem`, `SupplierInvoice` models.
        - Enhanced `Supplier` model with address and financial fields.
        - Created `PurchaseOrderService` with state machine.
        - Added `InventoryService` for centralized stock adjustments.
        - Created API endpoints for PO CRUD and receiving.
        - Fixed email validation (empty string → None conversion).
        - **Auto-SKU generation**: Products can be created without SKU (`PRD-YYYYMMDD-XXXX`).
    - **Frontend**:
        - Created `SuppliersModule` with lazy loading.
        - Implemented `SupplierDetailComponent` with modern styling.
        - Implemented `PurchaseOrderListComponent` and `PurchaseOrderEditComponent`.
        - Added `ReceivingDialogComponent` for item check-in.
        - Implemented product autocomplete in PO line items.
        - **QuickProductDialogComponent**: AI-ready badge, auto-SKU toggle, variant link.
        - **Common form styles** (`_forms.scss`) for consistent UI.
        - **Shipping & Additional Costs** section with intuitive labels and hints.
        - **Return-to-PO navigation** from product form.
    - **Tests**: Backend tests passing (receiving: 2/2, products: 15/15).
    - **Docs**: Updated `supplier-management.md` with new feature guides.

- **Deferred**:
    - AI Invoice Processing (LLM integration pending)
    - Dashboard Widgets (customizable analytics views)
