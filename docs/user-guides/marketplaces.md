# User Guide: Marketplaces

The **Marketplaces** tab allows you to connect Fulcrum to external sales
channels like Amazon and MercadoLibre, enabling centralized multi-channel
management.

## Accessing Marketplaces

Click **Marketplaces** in the left sidebar.

## Marketplace Overview

The main view shows all connected marketplace accounts with their sync status.

### Supported Platforms

| Platform     | Region             | Features                        |
| ------------ | ------------------ | ------------------------------- |
| Amazon       | North America (NA) | Inventory sync, pricing, orders |
| MercadoLibre | Mexico (MLM)       | Listings, orders, fulfillment   |

## Connecting a Marketplace

### Step 1: App Credentials (Admin)

Before connecting personal accounts, an administrator must configure the
platform's **App Credentials**:

1. Go to **Settings > Marketplaces**.
2. Click **Configure** next to Amazon or MercadoLibre.
3. Enter:
   - **Client ID** (App ID)
   - **Client Secret**
4. Save.

> See the
> [Marketplace Credential Setup Guide](../guides/marketplace-credential-setup.md)
> for detailed instructions on obtaining these credentials.

### Step 2: Connect Your Account

1. From the **Marketplaces** tab, click **+ Connect Account**.
2. Select the platform (Amazon or MercadoLibre).
3. Click **Authorize**.
4. You'll be redirected to the marketplace's login page.
5. Grant Fulcrum permission to access your seller data.
6. You'll be redirected back to Fulcrum with the connection established.

## Managing Listings

### Viewing Listings

Click on a connected account to see all synced listings.

### Syncing Inventory

1. Select products to sync.
2. Click **Sync Inventory** to push current stock levels to the marketplace.

### Publishing New Listings

1. From the product details, click **Publish to Marketplace**.
2. Select the target marketplace account.
3. Review/map fields (title, price, description).
4. Click **Publish**.

## AI-Powered Listing Generation

Fulcrum includes AI-powered tools to create optimized marketplace listings with
professional titles, compelling descriptions, and SEO keywords.

### How to Access

1. Navigate to **Products** and click on any product to open the details dialog.
2. Scroll to the **Marketplaces** section.
3. Click **Create Listing**.

### Generating Content with AI

1. In the Create Listing dialog, select your target marketplace:
   - **Amazon** – Professional, SEO-focused English content
   - **MercadoLibre** – Friendly Spanish content for Latin American audiences
   - **eBay** – Casual, deal-oriented English content
2. Click **Generate with AI** (requires AI to be enabled in Settings).
3. The AI will populate:
   - **Title** – Optimized for marketplace search algorithms
   - **Description** – Marketing-focused product description
   - **Keywords** – SEO tags for improved discoverability
4. Edit the generated content as needed.
5. Click **Save** to store the draft listing.

> **Note**: The "Generate with AI" button only appears if AI features are
> enabled in **Settings > AI**.

### Using Generated Keywords

The AI generates suggested keywords based on your product attributes. These
keywords are designed for use in:

- Marketplace backend keyword/tag fields
- Ad campaigns and sponsored listings
- Search engine optimization

To copy all keywords at once, click the **copy icon** next to the keywords
section. The keywords will be copied as a comma-separated list.

### Draft Listings

Saved listings are stored as **drafts** in Fulcrum. They contain:

- Title, description, and keywords in the `metadata_json` field
- Marketplace association
- Sync status (PENDING until published)

## Stock Transfers (Allocation Workflow)

Fulcrum keeps Purchase Order receiving separate from marketplace stock so you
can decide explicitly how much inventory goes to which channel. The path from
"received from supplier" to "available on MercadoLibre Full / Amazon FBA" goes
through a **Stock Transfer**.

### Mental model

Every product can have stock at multiple locations:

- `default` — your own warehouse.
- `ml-full` — MercadoLibre Full's fulfillment warehouse.
- `amazon-fba` — Amazon FBA's fulfillment warehouse.

A stock transfer is a planned movement between two of those locations under an
explicit state machine: **Draft → Shipped → Partially received → Received**
(plus **Cancelled** before ship).

### Accessing Stock Transfers

In the sidebar, expand **Marketplaces** and click **Stock Transfers**. The list
header has three top-level actions:

- **New Transfer** — create a single draft against one destination.
- **Allocation planner** — plan splits across multiple destinations in one pass.
- **Reconciliation** — view shrinkage / damage across received transfers.

### Creating and shipping a transfer

1. Click **New Transfer**. Pick the destination (MercadoLibre Full or Amazon
   FBA), search for products, set the units per row.
2. Click **Create draft**. You land on the detail page with status **Draft**.
3. When you actually ship the goods, either:
   - **Mark shipped** — pure status change, useful for tracking internally.
   - **Ship + reserve inbound** — also calls the marketplace's API to reserve an
     inbound shipment and stores the returned `external_inbound_id` on the
     transfer. This is the typical path for ML Full / Amazon FBA.
4. Status flips to **Shipped**; the source-location stock is decremented and an
   inventory adjustment row is written for the audit trail.

### Receiving and reconciling

When the destination warehouse confirms receipt (manually entered or, in the
future, via webhook):

1. Open the transfer detail and click **Receive items**.
2. The dialog pre-fills each line with the remaining shipped quantity. Adjust if
   the warehouse reported a different count.
3. Click **Record receipt**. Status moves to **Partially received** or
   **Received** depending on whether all lines are complete.

If `qty_received` ends up different from `qty_shipped`, the line shows up on the
**Reconciliation** page (shrinkage if negative, over-receipt if positive), so
discrepancies don't get lost.

### Pushing the new quantity to listings

Once a transfer is **Received** (or **Partially received**), the detail page
exposes **Push qty to listings**. This calls the marketplace's API and updates
the `available_quantity` on every `marketplace_listing` whose product appears in
the transfer.

The result panel reports three categories:

- ✅ Listings that synced successfully.
- ❌ Listings whose sync failed (with the error message — usually a
  missing/expired OAuth token).
- ⚠️ Products that have no marketplace listing yet — create those listings
  manually before they will sync.

### Allocation planner

If you want to split a batch of received inventory across multiple destinations
in one pass:

1. From **Stock Transfers**, click **Allocation planner**.
2. The table shows each product with its current quantity at internal,
   MercadoLibre Full, and Amazon FBA locations.
3. Enter values in **Send to ML** and **Send to Amazon** per row. The
   **Remaining internal** column updates live; over-allocating a product
   highlights the row and disables the save button.
4. Click **Create draft transfers**. Fulcrum creates **one DRAFT transfer per
   destination** bundling every product allocated to that destination.

Each draft is then shipped / received like any other transfer.

### Note on Purchase Order receiving

PO receiving updates **internal stock only**. Pushing that stock to a
marketplace warehouse is always an explicit Stock Transfer, never an automatic
side-effect of receiving a PO.

## Order Management

Incoming orders from marketplaces appear in the **Orders** section (if enabled).
Fulcrum can:

- Automatically import new orders.
- Update stock levels upon order placement.
- Provide fulfillment status updates.

> **Note**: Full order management features are in active development.

---

_Last Updated: May 2026_
