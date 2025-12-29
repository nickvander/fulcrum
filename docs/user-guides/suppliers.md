# User Guide: Suppliers & Purchase Orders

The **Suppliers** tab helps you manage your vendor relationships and track
inbound inventory through Purchase Orders (POs).

## Accessing Suppliers

Click **Suppliers** in the left sidebar.

## Managing Suppliers

### Adding a Supplier

1. Click **+ Supplier**.
2. Fill in the supplier details:
   - **Name**: Company or contact name.
   - **Contact Email**: For communication.
   - **Phone**: Optional.
   - **Address**: Optional shipping/billing address.
   - **Lead Time (Days)**: Average time from order to delivery.
3. Click **Save**.

### Supplier Details

Click on a supplier to view:

- Contact information.
- Associated products (if linked).
- Purchase order history.

## Purchase Orders

Purchase Orders track your inbound inventory from suppliers.

### Creating a Purchase Order

1. From the Suppliers list, click on a supplier, then **+ New PO**.
2. Or navigate directly to **Purchase Orders** and click **+ New PO**.
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
