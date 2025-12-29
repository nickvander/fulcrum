# User Guide: Suppliers & Purchase Orders

The **Suppliers** tab helps you manage your vendor relationships and track
inbound inventory through Purchase Orders (POs).

## Accessing Suppliers

Click **Purchasing > Suppliers** in the left sidebar.

## Managing Suppliers

### Supplier List Features

- **Sorting**: Click column headers (Supplier, Contact, Orders, Total Value) to sort the list.
- **KPIs**: View total number of suppliers at a glance.
- **Deep Linking**: Click the "X POs" button in the **Orders** column to view all purchase orders for that specific supplier.

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

- **Sorting**: Click any column header (PO #, Supplier, Status, Total, Date) to sort.
- **Supplier Filter**: Use the "Supplier" dropdown to filter orders by a specific vendor.
- **Status Filter**: Filter by Draft, Ordered, Received, etc.
- **Date Range**: Use the presets (Today, This Week, Month to Date) to focus on recent activity.
- **KPI Summary**: View Total Orders, Pending count, Total Value, and Received Value at the top.

### Creating a Purchase Order

1. From the **Purchase Orders** screen, click **+ Create PO**.
2. Or from the **Suppliers** list, click **+ Add PO**.
3. Select the **Supplier** (if not pre-selected).
4. Add **Line Items**:
   - Search for products or add new ones.
   - Specify quantity and unit cost.
5. Review totals (Subtotal, Tax, Shipping, Total).
6. Set **Status**: Draft, Ordered, Received.
7. Click **Save**.

### PO Statuses

| Status   | Description                                       |
| -------- | ------------------------------------------------- |
| Draft    | PO is being prepared, not yet sent to supplier.   |
| Ordered  | PO has been sent/submitted to the supplier.       |
| Received | Goods have arrived and inventory has been updated.|

### Receiving Inventory

When goods arrive:

1. Open the PO.
2. Click **Mark as Received**.
3. The system automatically updates product stock quantities and recalculates
   average cost based on the new purchase price.

## Linking Products to Suppliers

You can associate products with specific suppliers for reorder tracking:

1. Go to **Products > [Product] > Edit**.
2. In the **Supplier Product** section, link to a supplier and specify their
   SKU.

---

_Last Updated: December 2025_
