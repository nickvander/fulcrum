# Future Usability Roadmap

## 1. Low Stock Dashboard

**Goal**: Proactive inventory management to prevent stockouts.

### Concept

A new "Dashboard" landing page widget or a dedicated "Inventory Health" view.

### Key Features

- **Critical Stock Widget**: List of items where `Quantity < Reorder Point`.
- **Velocity Tracking**: "Fast Movers" list to highlight items selling quickly.
- **Visual Indicators**: Red/Yellow/Green status bars for stock levels.

### Implementation Plan

1.  **Backend**:
    - Add `reorder_point` and `reorder_quantity` to `Product` model (if not
      exists).
    - Create `/reports/low-stock` endpoint.
2.  **Frontend**:
    - Create `DashboardModule`.
    - Build `LowStockWidgetComponent` with "Create PO" action.

---

## 2. Reorder Workflow (Shopping Cart Style)

**Goal**: Simplify multisupplier reordering into a single, cohesive flow.

### Workflow

1.  **Collect**: User browses "Low Stock" list or Product Catalog.
2.  **Add to List**: Instead of "Create PO" immediately, user clicks "Add to
    Reorder List" (like a shopping cart).
3.  **Review**: User opens "Reorder List" drawer.
    - Items are grouped by Supplier automatically.
4.  **Generate**: User clicks "Create Purchase Orders".
    - System generates _separate_ Draft POs for each supplier.
5.  **Refine & Send**: User is taken to a "Bulk PO Review" screen (or list of
    drafts) to finalize and email them.

### Implementation Plan

- **State Management**: Use a local store (or service) to track the temporary
  "Reorder List".
- **Batch Action**: "Create POs from List" button.

---

## 3. Marketplace Integration Engine

**Goal**: Modular, scalable connection to external platforms (Amazon, eBay,
AliExpress, Shopify).

### Architecture: "Adapter Pattern"

We will build a plugin-style architecture where each marketplace is an
"Adapter".

**Core Interface (`MarketplaceAdapter`):**

- `fetch_orders(since_date)`
- `sync_inventory(sku, quantity)`
- `get_product_details(external_id)`

**Workflow:**

1.  **Configuration**: User enters API keys for enabled platforms (e.g., in
    Settings > Integrations).
2.  **Sync Job**: A background task (Celery) runs every X minutes.
    - Iterates through enabled Adapters.
    - Fetches new orders -> Creates Sales Orders in Fulcrum.
    - Updates Fulcrum Inventory -> Pushes new Qty to all Adapters.

### Implementation Plan

1.  **Backend**: Define `BaseMarketplaceAdapter` abstract class.
2.  **Backend**: Implement a concrete `AmazonAdapter` (using SP-API) or
    `ShopifyAdapter` as a pilot.

---

## 4. Supplier Catalog Import

**Goal**: Standardize ingestion of messy supplier spreadsheets without requiring
AI for every case.

### Non-AI Approach: "Map & Template"

1.  **Upload**: User uploads a CSV/Excel file from a supplier.
2.  **Mapping Screen**:
    - System shows first 5 rows.
    - User maps Columns: "Supplier Header: `Item #`" -> "Fulcrum Field:
      `Supplier SKU`".
    - User maps Columns: "Supplier Header: `Cost`" -> "Fulcrum Field:
      `Cost Price`".
3.  **Save Template**: User saves this mapping as "Global Industrial Template".
4.  **Process**: System ingests the file using the saved map.
5.  **Future Uploads**: User selects "Global Industrial Template", and the
    system auto-processes the file.

### Implementation Plan

- **DB**: `ImportTemplate` model (stores JSON mapping of column indices/names).
- **Frontend**: A drag-and-drop mapping UI (similar to Table Import tools).
