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

> **Coming Soon**: Direct publishing to marketplace APIs with automatic
> inventory synchronization.

## Order Management

Incoming orders from marketplaces appear in the **Orders** section (if enabled).
Fulcrum can:

- Automatically import new orders.
- Update stock levels upon order placement.
- Provide fulfillment status updates.

> **Note**: Full order management features are in active development.

---

_Last Updated: January 2026_
