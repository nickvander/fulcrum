# Supplier and Purchase Order Management

This guide details the system's capabilities for managing Suppliers, Purchase
Orders (POs), and inbound inventory.

## Supplier Management

Suppliers are the external entities from whom you source products. The system
allows you to maintain detailed records for each supplier.

### Key Fields

- **Contact Info**: Name, Email, Phone, Primary Contact Person.
- **Address**: Street, City, State, Zip, Country.
- **Financials**:
  - **Tax ID**: For regulatory compliance.
  - **Payment Terms**: e.g., "Net 30", "Due on Receipt".
  - **Currency**: Default currency for the supplier (e.g., USD, EUR).
- **Details**: Website, Internal Notes.

### Product Integration

Each product can be linked to a primary `Supplier`. You can also specify a
**Supplier SKU** (`supplier_sku`), which is the unique identifier the supplier
uses for that product (which may differ from your internal SKU).

**Managing Supplier Products:**

1. Navigate to a **Supplier Detail** page.
2. Click the **Products** tab.
3. View all products sourced from this supplier, including cost and lead times.
4. Click on a **Product Name** to navigate to its full details page for editing.

### Viewing Product Sources

```bash
# Get all suppliers for a product
GET /api/v1/supplier-products/by-product/{product_id}
# Get all products from a supplier
GET /api/v1/suppliers/{id}/products
```

## Smart Purchase Order Creation

When adding products to a Purchase Order (e.g., from the Inventory Health
Widget), the system provides intelligent automation:

### Automatic Supplier Selection

- **Single Supplier**: If a product is sourced from only one supplier, that
  supplier is automatically selected for the PO and the cost is pre-filled.
- **Multiple Suppliers**: A dialog prompts you to choose which supplier to use,
  showing cost, lead time, and SKU for each option.
- **Fallback**: If no supplier-product associations exist, the product's default
  supplier is used.

### Bundle Unpacking

When adding a **bundle** product to a PO:

- The system **automatically unpacks** the bundle into its individual
  components.
- Each component is added as a separate line item with the correct quantity.
- Supplier selection logic applies to each component individually.
- The bundle itself is NOT added to the PO (since you order the components, not
  assembled bundles).

**Example**: Adding "Starter Kit" bundle (contains 2x Widget A, 1x Widget B)
results in two line items: Widget A (qty 2) and Widget B (qty 1).

## Purchase Order Lifecycle

Purchase Orders track the lifecycle of ordering stock from suppliers.

### Lifecycle Statuses

1.  **Draft**: PO is being built. Line items can be added/removed.
2.  **Ordered**: PO has been sent to the supplier.
3.  **Partially Received**: Some items have arrived, but not all.
4.  **Completed**: All items have been received.
5.  **Completed**: All items have been received.
6.  **Closed**: PO is finalized and no further action is expected.

### Deleting Purchase Orders

You can delete a Purchase Order only if:

- It is in **Draft** or **Ordered** status.
- **No items have been received yet.**

If you have already received items, the system will block deletion to preserver
inventory integrity. To "cancel" such an order, you should manually adjust stock
if needed and mark the PO as **Closed**.

### Order Safety (Locking)

To prevent accidental edits, Purchase Orders are automatically **Locked** when
they move out of `Draft` status (e.g., to `Ordered` or `Received`).

- **Read-Only**: All fields become read-only to ensure data integrity.
- **Unlock to Edit**: If you must make changes, click the **"Unlock to Edit"**
  button. This requires confirmation and re-enables all fields.
- **Best Practice**: Only unlock orders if absolutely necessary, as changing
  quantities on an active order can affect receiving logic.

### Cost Tracking

- **Unit Cost**: The cost per item at the time of ordering.
- **Additional Costs**:
  - **Shipping Cost**: Freight/Transport fees.
  - **Tax Amount**: Sales tax or VAT.
  - **Other Costs**: Customs duties, insurance, etc.
- **Landed Cost**: The system will eventually calculate the total landed cost
  per unit by allocating these additional costs across the received items.

### Invoices

The system supports attaching **Supplier Invoices** (PDF/Image) to POs. In the
future, AI-powered parsing will extract invoice data automatically to facilitate
3-way matching (PO vs Receipt vs Invoice).

## Receiving Workflow

When items arrive from a supplier, you can record the receipt against a Purchase
Order.

### How to Receive Items

1. Navigate to **Suppliers → Purchase Orders**.
2. Click on a PO with status "Ordered" or "Partially Received".
3. Click the **"Receive Items"** button.
4. The **Receiving Dialog** will open, showing a card for each product with its
   image and status.
5. Enter the `quantity_to_receive` for the relevant items.
6. Click **"Receive"** to confirm.

### What Happens on Receive

- **PO Item Update**: The `quantity_received` field is incremented.
- **Inventory Update**: Stock levels are automatically increased.
- **Status Transition**:
  - If some items are received: Status → **Partially Received**
  - If all items are received: Status → **Completed**
- **Audit Trail**: An `InventoryAdjustment` record is created with reason
  "Received PO #X".

## Creating Purchase Orders

### Adding Line Items with Product Search

When creating a PO, you can search for products by name or SKU:

1. In the **Product** field, type at least 2 characters.
2. Matching products will appear in a dropdown.
3. Select a product to auto-fill the ID and cost.

### Quick-Add Product

If the product doesn't exist:

1. Type the product name in the search field.
2. Click the **+** icon next to the Product field.
3. Fill in Name and pricing. SKU is auto-generated if left blank.
4. Click **"Create Product"** - it will be auto-selected.

### Auto-Generated SKU

Products can be created without specifying a SKU. The system will automatically
generate a unique SKU in the format:

```
PRD-YYYYMMDD-XXXX
```

Where:

- `PRD` = Product prefix
- `YYYYMMDD` = Date of creation
- `XXXX` = Random 4-character hex code

### Creating Products with Variants

If you need to add a product with variants (size, color, etc.):

1. Click **"Create and continue editing"** in the Quick-Add dialog.
2. The product is created and you're taken to the full product form.
3. A **"Return to Purchase Order"** banner appears at the top.
4. Add your variants in the Product Variants section.
5. Click the banner to return to your PO with state preserved.

## Shipping & Additional Costs

When creating a PO, you can track extra costs beyond product prices:

| Field                       | Description                 |
| --------------------------- | --------------------------- |
| **Shipping / Freight**      | Delivery and transport fees |
| **Customs / Import Duties** | Taxes on imported goods     |
| **Other Fees**              | Insurance, handling, etc.   |

### Distributing Costs to Line Items

1. Enter your additional costs in the respective fields.
2. The system calculates the **total extra costs** and **cost per unit**.
3. Click **"Add to Unit Costs"** to open the Cost Allocation Preview.
4. Review the itemized breakdown showing how costs will be distributed.
5. **Exclude Items**: Uncheck items that should not receive any cost allocation
   (e.g., service items).
6. Click **"Apply Costs"** to confirm.

> **Note on Drafts**: To use advanced features like Cost Allocation or Invoice
> Upload on a new order, the system will prompt you to save the order as a
> **Draft** first. This ensures your data is safe and allows complex operations
> to run on the server.

### Cost Breakdown Tracking

The system tracks exactly where each dollar of your product cost came from:

| Field                | Description                      |
| -------------------- | -------------------------------- |
| `base_cost`          | Original supplier price per unit |
| `shipping_allocated` | Freight portion added per unit   |
| `taxes_allocated`    | Import duties added per unit     |
| `other_allocated`    | Other fees added per unit        |
| `costs_applied_at`   | When costs were allocated        |

This allows you to review cost history and understand true product costs.

## Invoice Management

You can attach supplier invoices (PDF or images) to Purchase Orders for
record-keeping.

### Uploading Invoices

1. Navigate to a Purchase Order (or start a new one and save as Draft).
2. In the Invoices section, click **"Upload Invoice"**.
3. Select a PDF, JPG, or PNG file (max 10MB).
4. Optionally enter the invoice number.
5. The invoice is securely stored and linked to the PO.

### Security

- **File types**: Only PDF, PNG, JPG, JPEG allowed
- **Size limit**: Maximum 10MB per file
- **Secure naming**: Files are renamed to UUIDs to prevent path traversal
  attacks

## Multi-Source Products

Products can be sourced from multiple suppliers, each with different prices and
SKUs.

### Adding Additional Suppliers

Use the `/supplier-products` API to manage product-supplier relationships:

```bash
# Add a product to a supplier
POST /api/v1/supplier-products/
{
  "product_id": 1,
  "supplier_id": 2,
  "supplier_sku": "VENDOR-SKU-123",
  "cost_price": 15.50,
  "lead_time_days": 7
}
```

### Setting Primary Supplier

Mark one supplier as the primary source for a product:

```bash
POST /api/v1/supplier-products/{id}/set-primary
```

The primary supplier's price is used as the default when creating POs.

### Viewing Product Sources

```bash
# Get all suppliers for a product
GET /api/v1/supplier-products/by-product/{product_id}

# Get all products from a supplier
GET /api/v1/supplier-products/by-supplier/{supplier_id}
```
