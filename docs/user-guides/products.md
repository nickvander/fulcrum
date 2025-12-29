# User Guide: Products

The **Products** tab is the central hub for managing your entire product
catalog. Here you can create, edit, and organize all your items—including
bundles (kits) that combine multiple products.

## Accessing the Products Tab

Click **Products** in the left sidebar. You'll see the main product list view.

## Product List View

The product list displays all your items in either **Grid** or **List** mode
(toggle in the top-right).

### Quick Filters

Use the quick filter chips to narrow down your view:

- **In Stock**: Shows only products with stock ≥ 1
- **Out of Stock**: Shows only products with stock = 0
- **Low Stock**: Shows products with stock ≤ 10

### Advanced Filters

Click the **Filters** button to expand the advanced filter panel:

| Filter       | Description                                     |
| ------------ | ----------------------------------------------- |
| Product Type | Filter by All, Products Only, or Bundles Only  |
| Min Price    | Show products priced at or above this value    |
| Max Price    | Show products priced at or below this value    |
| Min Stock    | Show products with stock at or above this level|
| Max Stock    | Show products with stock at or below this level|

> **Tip**: Filters are **debounced** — the list only refreshes after you stop
> typing for 400ms, preventing excessive loading.

## Creating a Product

1. Click the **+ Product** button in the header.
2. Fill in the required fields:
   - **Name**: Display name of the product.
   - **SKU**: Unique identifier (auto-generated if left blank).
   - **Cost Price**: Your acquisition cost per unit.
   - **Resale Price**: Your selling price.
3. Optionally add:
   - **Description**: Detailed product description (AI can help generate this!).
   - **Images**: Drag and drop or click to upload.
   - **Custom Fields**: Add key-value pairs for metadata.
4. Click **Save**.

## Creating a Bundle

Bundles are virtual products composed of other items. Stock is calculated
dynamically based on component availability.

1. Click the **+ Bundle** button in the header.
2. Fill in the bundle details (Name, SKU, Price).
3. In the **Bundle Components** section:
   - Search for products to add.
   - Specify the quantity of each component.
4. The **Estimated Cost** is automatically calculated from component costs.
5. Click **Save**.

> **Note**: When viewing a bundle in the product list, you'll see stock
> displayed as: `Total X (Y allocated) = Z available`.

## Editing a Product

Click on any product card (Grid view) or row (List view) to open the **Product
Details Dialog**.

- **View Mode**: Shows product information, images, inventory status, and
  purchase history.
- **Edit Mode**: Click the **Edit** button to modify fields and save.

## Stock Management

From the product details dialog or the action menu (⋮) on the product card:

- **Adjust Stock**: Add or remove inventory with a reason.
- **View Stock History**: See all previous adjustments.

For bundles, you can **Allocate/Reserve Stock** to pre-build kits from component
inventory.

## Batch Operations

Select multiple products using the checkboxes, then use the batch action toolbar
to:

- Delete selected products.
- Update prices in bulk.
- Assign categories or custom fields.

---

_Last Updated: December 2025_
