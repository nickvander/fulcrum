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

## Order Management

Incoming orders from marketplaces appear in the **Orders** section (if enabled).
Fulcrum can:

- Automatically import new orders.
- Update stock levels upon order placement.
- Provide fulfillment status updates.

> **Note**: Full order management features are in active development.

---

_Last Updated: December 2025_
