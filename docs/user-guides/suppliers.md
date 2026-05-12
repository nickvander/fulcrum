# User Guide: Suppliers & Purchase Orders

The **Suppliers** tab helps you manage your vendor relationships and track
inbound inventory through Purchase Orders (POs).

## Accessing Suppliers

Click **Purchasing > Suppliers** in the left sidebar.

## Managing Suppliers

### Supplier List Features

- **Sorting**: Click column headers (Supplier, Contact, Orders, Total Value) to
  sort the list.
- **KPIs**: View total number of suppliers at a glance.
- **Deep Linking**: Click the "X POs" button in the **Orders** column to view
  all purchase orders for that specific supplier.

### Adding a Supplier

1. Click **+ Add Supplier**.
2. Fill in the supplier details:
   - **Name**: Company or contact name.
   - **Contact Email**: For communication.
   - **Phone**: Optional.
   - **Address**: Optional shipping/billing address.
   - **Lead Time (Days)**: Average time from order to delivery.
3. Click **Save**.

### Supplier Details

Click on a supplier row or "Edit" button to view:

- Contact information.
- Associated products (if linked).
- Purchase order history.

## Purchase Orders

Purchase Orders track your inbound inventory from suppliers.

### Accessing Purchase Orders

Click **Purchasing > Purchase Orders** in the left sidebar.

### Purchase Order List Features

The PO list is designed for efficiency:

- **Sorting**: Click any column header (PO #, Supplier, Status, Total, Date) to
  sort.
- **Supplier Filter**: Use the "Supplier" dropdown to filter orders by a
  specific vendor.
- **Status Filter**: Filter by Draft, Ordered, Received, etc.
- **Date Range**: Use the presets (Today, This Week, Month to Date) to focus on
  recent activity.
- **KPI Summary**: View Total Orders, Pending count, Total Value, and Received
  Value at the top.

### Creating a Purchase Order

1. From the **Purchase Orders** list, click **+ Create PO**.
2. **AI-Powered Fast Start (Optional):**
   - If AI features are enabled, you'll see a drop zone at the bottom: **"Drop
     invoice to extract PO details"**.
   - Drag & drop your invoice file here.
   - The AI will automatically fill in the Supplier, Currency, Shipping/Tax
     costs, and add matching Line Items.
3. **Manual Entry:**
   - Select the **Supplier** (if not auto-selected).
   - Add **Line Items**: Search for products or add new ones.
   - Set **Status**: Draft, Ordered, Received.
4. Click **Save**.

### PO Statuses

| Status   | Description                                        |
| -------- | -------------------------------------------------- |
| Draft    | PO is being prepared, not yet sent to supplier.    |
| Ordered  | PO has been sent/submitted to the supplier.        |
| Received | Goods have arrived and inventory has been updated. |

### Receiving Inventory

When goods arrive:

1. Open the PO.
2. Click **Mark as Received**.
3. The system automatically updates product stock quantities and recalculates
   average cost based on the new purchase price.

### Invoice Matching (AI-Powered)

When you receive an invoice from your supplier, Fulcrum can automatically match
it against your PO using AI.

#### How It Works

1. Open the PO you want to match an invoice against.
2. Scroll to the **Supplier Invoices** section.
3. **Drag & Drop** your invoice file into the zone labeled "Drop invoice
   here..."
   - A purple **AI-Powered** badge indicates smart extraction is active.
4. The AI extracts vendor, items, and costs automatically.
5. Review the matching results:
   - 🟢 **Matched** - Items match exactly
   - 🟡 **Diff** - Quantity or price differs
   - 🔴 **Unmatched** - Item not found in PO
6. Click **Apply Invoice Values** to update PO costs.
7. **Save** your PO to persist changes.

> **Note:** "Import Invoice" is only available for Draft/Ordered POs.

## Import PO vs. Create PO: What's the Difference?

Fulcrum offers two ways to create Purchase Orders from supplier documents:

| Feature         | Import PO (Dialog)                                      | Create PO (Form)                                             |
| --------------- | ------------------------------------------------------- | ------------------------------------------------------------ |
| **Use When**    | You want a wizard-style flow to scan > preview > create | You want to verify/edit details immediately on the full form |
| **How**         | PO List → Import PO → Upload document                   | Create PO → Drag invoice to bottom drop zone                 |
| **Result**      | Creates new PO with extracted data                      | Pre-fills form with extracted data                           |
| **Flexibility** | Best for quick ingestion                                | Best for checking details as you go                          |

### Recommended Workflow

```
1. Create PO manually OR Import PO from supplier quote
   └─> Order sent to supplier → Status: Ordered

2. Goods arrive + Invoice received
   └─> Open PO → Import Invoice → Match & apply costs
   └─> Verify discrepancies (price changes, qty diffs)

3. Receive items
   └─> Mark as Received → Inventory updated
```

### Import Review Match Assistance

Imported supplier documents are staged in a review queue before they create a
draft PO. If a supplier line item is unmatched, use the review dialog to resolve
it before approval:

- **Create product** creates a new Fulcrum product from the supplier line, links
  it to the selected supplier, learns the supplier SKU/name as an alias, and
  marks that review line as matched.
- **Learn alias** is available after selecting an existing Fulcrum product. It
  saves the supplier SKU/name as a learned alias for future imports and marks
  the current review line as matched.

Approving an import review still creates a draft PO only. Inventory changes only
after the PO is received.

## Linking Products to Suppliers

You can associate products with specific suppliers for reorder tracking:

1. Go to **Products > [Product] > Edit**.
2. In the **Supplier Product** section, link to a supplier and specify their
   SKU.

---

## Testing Invoice Matching

Sample invoices are provided for testing both workflows:

**Location:** `backend/samples/purchase_orders/`

| File                           | Vendor               | Best For                       |
| ------------------------------ | -------------------- | ------------------------------ |
| `tech_supplies_direct_po.html` | Tech Supplies Direct | Testing with electronics items |
| `home_essentials_po.html`      | Home Essentials Co.  | Testing with home goods        |
| `global_electronics_po.html`   | Global Electronics   | Testing with computer parts    |
| `mexitech_po_spanish.html`     | Mexitech             | Spanish language invoice       |
| `fashion_forward_po.txt`       | Fashion Forward      | Plain text format              |

### Test Mode 1: Import PO (Create New)

1. Go to **Purchase Orders** list
2. Click **Import PO** button
3. Upload one of the sample files above
4. Review extracted data (vendor, items, costs) 5.Click **Create PO** to save

### Test Mode 2: Import Invoice (Match Existing)

1. Create a PO manually with items matching a sample invoice
   - For `home_essentials_po.html`: Add products with SKUs like `HE-LAMP-DESK`
2. Save the PO
3. Open the PO and scroll to **Supplier Invoices**
4. Click **Import Invoice** and upload the matching sample file
5. Review the matching dialog - items should match with confidence scores
6. Click **Apply Invoice Values** to update costs
7. Save the PO

---

_Last Updated: January 2026_
