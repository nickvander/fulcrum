# Phase 5: Supplier Order Management & AI Invoicing

**Goal:** Implement a comprehensive system for managing suppliers, purchase orders (POs), and inbound shipments, enhanced by AI for automated invoice processing.

## 1. Feature Scope

### 1.1 Supplier Management (Foundation)
- **Enhanced Supplier Model**:
    - **Physical Address**: Street, City, State/Province, Postal Code, Country.
    - **Financials**: Tax ID / VAT Number, Payment Terms (e.g., Net 30, Due on Receipt).
    - **Details**: Website URL, Internal Notes (Rich Text).
    - **Contact**: Primary Contact Name, Email, Phone (Existing).
- **Multi-Currency Support**:
    - Allow assigning a default currency (USD, EUR, etc.) to a supplier.
    - Store exchange rates on Purchase Orders (frozen at time of order or invoice).

### 1.2 Product-Supplier Relationship
- **Primary Supplier (Default)**:
    - Leveraging the existing `supplier_id` on the Product model.
    - Used to auto-fill POs when reordering.
    - **Supplier SKU**: Add `supplier_sku` to Product model (separate from internal SKU).
- **Multi-Source (Future)**:
    - Designing schema to allow a `SupplierProduct` join table in the future for products available from multiple vendors with different costs/SKUs.

### 1.2 Purchase Orders (PO)
- **Lifecycle**: Draft -> Ordered -> Partially Received -> Completed -> Closed.
- **Creation**:
    - Manual entry of line items (Product selection).
    - Auto-fill cost price from Product master.
    - Support for tax and miscellaneous costs.

### 1.3 Invoice Processing (Hybrid)
- **Manual Entry (Default)**:
    - Standard UI to manually input invoice details against a Purchase Order.
    - **File Attachment**: Ability to upload and attach PDF/Image receipts to the PO for record-keeping without parsing.
    - Side-by-side view: Show attached PDF on one side while manually entering line items.
- **AI-Powered Automation (Optional)**:
    - **Configuration**: User can toggle "AI Invoice Parsing" in settings.
    - **Workflow**: If enabled, uploaded files are sent to LLM for extraction.
    - **Fallback**: If AI fails or is disabled, system reverts to standard file attachment flow.

### 1.4 Receiving & Inventory Check-In
- **Receiving Wizard** (accessible from PO or Products page):
    - "Select PO to Receive" or "Receive from Invoice".
    - partial receiving support (e.g., received 5/10 items).
    - **Inventory Update**: Automatically increment stock at specific location upon check-in.
    - **Batch/Lot Tracking** (Optional foundation for future).

### 1.5 Landed Cost Tracking
- **Cost Allocation**:
    - Input global "Shipping/Import Cost" for a PO/Shipment.
    - options to allocate by: Value, Weight, or Quantity.
- **Cost Price Update**: Logic to update the "Average Cost" of products based on the landed cost.

## 2. Technical Architecture

### Backend (FastAPI)
- **New Models**:
    - `PurchaseOrder` (supplier_id, status, currency, exchange_rate, total, landed_costs)
    - `PurchaseOrderItem` (po_id, product_id, qty_ordered, qty_received, unit_cost)
    - `SupplierInvoice` (raw_file_path, parsed_data_json)
- **Services**:
    - `PurchaseOrderService`: State machine for POs.
    - `InventoryService`: Handle check-in transactions.
    - `InvoiceParserService`: Abstraction that checks `AppSettings` before calling AI provider.

### Frontend (Angular)
- **Modules**: `SupplierModule` (lazy loaded).
- **Components**:
    - `SupplierListComponent`, `SupplierDetailComponent`
    - `PurchaseOrderListComponent`, `PurchaseOrderEditComponent`
    - `ReceivingWizardComponent`
    - `InvoiceUploadComponent` (file handling + preview)

## 3. Implementation Phases

1.  **Foundation**: DB Migrations for POs, Items, and enhanced Suppliers. [x]
2.  **PO Management**: Basic CRUD for POs (Manual creation). [x]
3.  **Receiving**: Logic to receive items and update stock. [x]
4.  **AI Ingestion**: File upload and Parsing pipeline.
5.  **Landed Costs**: Cost allocation logic.
