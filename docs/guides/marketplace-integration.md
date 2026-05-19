# Marketplace Integration Guide

This guide covers how to set up and configure integrations with external
marketplaces (Amazon SP-API and MercadoLibre) for Fulcrum.

> **Last Updated**: May 2026

## Supported Marketplaces

| Marketplace  | Region    | Site ID        | Auth URL                              |
| ------------ | --------- | -------------- | ------------------------------------- |
| Amazon       | US        | ATVPDKIKX0DER  | `https://sellercentral.amazon.com`    |
| Amazon       | Mexico    | A1AM78C64UM0Y8 | `https://sellercentral.amazon.com.mx` |
| MercadoLibre | Mexico    | MLM            | `https://auth.mercadolibre.com.mx`    |
| MercadoLibre | Argentina | MLA            | `https://auth.mercadolibre.com.ar`    |
| MercadoLibre | Brazil    | MLB            | `https://auth.mercadolivre.com.br`    |
| MercadoLibre | Colombia  | MCO            | `https://auth.mercadolibre.com.co`    |

---

## Amazon SP-API Integration

### 2025 Updates

> [!IMPORTANT] **Key Changes in 2025:**
>
> - **No AWS IAM Required**: Since October 2023, SP-API no longer requires AWS
>   IAM or Signature Version 4. Authentication is now purely OAuth 2.0 (LWA).
> - **JSON-Only**: As of July 31, 2025, XML and Flat File Listings Feeds have
>   been removed. All API interactions are now JSON-based.
> - **Third-Party Developer Fees** (starting 2026):
>   - Annual subscription: $1,400 USD (from Jan 31, 2026)
>   - Monthly API usage fee based on GET call volume (from April 30, 2026)
>   - Self-use by sellers/vendors is **exempt** from these fees.

### Prerequisites

1. **Amazon Seller Account**: You need an active Amazon Professional Seller
   account.
2. **Developer Registration**: Register as an SP-API developer at
   [Amazon Developer Central](https://developer.amazonservices.com/).

### Step 1: Register as an SP-API Developer

1. Go to [Amazon Seller Central](https://sellercentral.amazon.com/) and log in.
2. Navigate to **Apps & Services > Develop Apps**.
3. Click **Register as a Developer**.
4. Fill in your organization details and accept the Developer Agreement.

### Step 2: Create an SP-API Application

1. In Developer Central, go to **Develop Apps > Add New App Client**.
2. Choose your application type:
   - **Private Seller App**: For your own organization only (self-authorized).
   - **Public App**: For third-party sellers (requires OAuth consent).
3. Fill in the required fields:
   - **App Name**: e.g., "Fulcrum Inventory Manager"
   - **API Type**: Selling Partner API
   - **OAuth Redirect URI**:
     `http://localhost:4200/marketplaces/amazon/callback` (or your production
     URL)
4. After submission, you'll receive:
   - **Client ID** (LWA Client Identifier)
   - **Client Secret** (LWA Client Secret)

### Step 3: Configure Fulcrum

You have two options to configure your credentials: user-specific via the
Settings UI (recommended) or globally via `.env` variables.

#### Option A: Settings UI (Recommended)

1. Go to **Marketplaces > Add Marketplace Account**.
2. Select **Amazon**.
3. Enter your **Client ID** and **Client Secret**.
4. Click **Save & Connect**.

#### Option B: Global Configuration (Alternative)

For single-tenant deployments, you can set defaults in your `.env` file:

```bash
# Amazon SP-API Configuration
AMAZON_CLIENT_ID=amzn1.application-oa2-client.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AMAZON_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AMAZON_REDIRECT_URI=http://localhost:4200/marketplaces/amazon/callback
```

### Step 4: OAuth Flow

1. User clicks "Connect Amazon" in Fulcrum.
2. Fulcrum redirects to Amazon's consent page.
3. Seller authorizes access.
4. Amazon redirects back with an `spapi_oauth_code`.
5. Fulcrum exchanges the code for tokens via
   `POST https://api.amazon.com/auth/o2/token`.
6. Tokens are encrypted and stored securely.

### Testing (Sandbox)

Amazon provides a **Sandbox environment** for testing:

- Use the same credentials but call sandbox endpoints.
- Sandbox base URL: `https://sandbox.sellingpartnerapi-na.amazon.com`
- See:
  [SP-API Sandbox](https://developer-docs.amazon.com/sp-api/docs/the-selling-partner-api-sandbox)

---

## MercadoLibre Integration

### 2025 Updates

> [!IMPORTANT] **Key Changes in 2025:**
>
> - **Authenticated Search Required**: Starting April 2025, the `/search`
>   endpoint requires authenticated user authorization. Anonymous product
>   searches are no longer supported.
> - **HTTPS Redirect URIs**: Production applications must use HTTPS for the
>   `redirect_uri`.
> - **Mexico Investment**: MercadoLibre is investing $3.4B in Mexico in 2025,
>   making it a priority market with enhanced API support.

### Prerequisites

1. **MercadoLibre Seller Account**: Active seller account in your target
   country.
2. **Developer Account**: Register at the MercadoLibre Developer Center.

### Step 1: Create a Developer Application

1. Go to the developer portal for your country:
   - **Mexico**: https://developers.mercadolibre.com.mx/
   - **Argentina**: https://developers.mercadolibre.com.ar/
   - **Brazil**: https://developers.mercadolivre.com.br/
2. Log in with your MercadoLibre account.
3. Navigate to **My Applications > Create New Application**.
4. Fill in the required fields:
   - **Application Name**: e.g., "Fulcrum Integration"
   - **Short Description**: Brief description of your integration.
   - **Redirect URI**:
     `http://localhost:4200/marketplaces/mercadolibre/callback`
5. After creation, you'll receive:
   - **App ID** (Client ID)
   - **Secret Key** (Client Secret)

> **Important**: In Mexico and some other countries, MercadoLibre requires
> identity validation of the account holder before the app can be activated.

### Step 2: Configure Fulcrum

#### Option A: Settings UI (Recommended)

1. Go to **Marketplaces > Add Marketplace Account**.
2. Select **MercadoLibre**.
3. Enter your **App ID** and **Secret Key**.
4. Click **Save & Connect**.

#### Option B: Global Configuration (Alternative)

For single-tenant deployments, set defaults in your `.env` file:

```bash
# MercadoLibre Configuration (Mexico)
ML_CLIENT_ID=1234567890123456
ML_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ML_REDIRECT_URI=http://localhost:4200/marketplaces/mercadolibre/callback
```

### Step 3: OAuth Flow

1. User clicks "Connect MercadoLibre" in Fulcrum.
2. Fulcrum redirects to `https://auth.mercadolibre.com.mx/authorization`.
3. User logs in and authorizes access.
4. MercadoLibre redirects back with an authorization `code`.
5. Fulcrum exchanges the code for tokens via
   `POST https://api.mercadolibre.com/oauth/token`.
6. Tokens are encrypted and stored securely.

### Multi-Country Support

To support a different country, update the `MercadoLibreConnector` class
constants:

```python
# For Argentina
SITE_ID = "MLA"
AUTH_URL = "https://auth.mercadolibre.com.ar/authorization"

# For Brazil
SITE_ID = "MLB"
AUTH_URL = "https://auth.mercadolivre.com.br/authorization"

# For Colombia
SITE_ID = "MCO"
AUTH_URL = "https://auth.mercadolibre.com.co/authorization"
```

> **Note**: The API base URL (`https://api.mercadolibre.com`) is the same for
> all countries.

### Testing

MercadoLibre provides **test users** for development:

1. Go to your application in the Developer Center.
2. Click **Create Test User**.
3. MercadoLibre generates a test seller account with credentials.
4. Use these credentials to test the OAuth flow and API calls without affecting
   real accounts.

---

## Stock Transfers & Marketplace Fulfillment

Fulcrum models inventory at marketplace fulfillment warehouses (ML Full, Amazon
FBA) as additional `inventory_items.location` values alongside the internal
`default` warehouse. Movement between locations always goes through the
`stock_transfers` workflow — PO receiving only ever updates internal stock.

### Connector surface

`BaseMarketplaceConnector` exposes two methods that subclasses can implement to
plug into the workflow:

```python
async def create_inbound_shipment(
    items: List[InboundShipmentItem],
    access_token: Optional[str] = None,
) -> InboundShipmentResult:
    """Reserve an inbound shipment at the marketplace warehouse."""

async def get_inbound_shipment_status(
    external_inbound_id: str,
    access_token: Optional[str] = None,
) -> InboundShipmentResult:
    """Poll the marketplace for inbound shipment receipt status."""
```

Both have default no-op stubs on the base class so existing connectors stay
valid. `MercadoLibreConnector` implements them against the `/fbm/inbound/...`
endpoints, with a deterministic stub fallback when no access token is present so
dev/test environments can run the workflow end-to-end without live API calls.

### Service & endpoints

`StockTransferService` orchestrates the workflow:

- `ship(transfer_id, push_to_marketplace=False)` — decrements source stock,
  marks SHIPPED. When `push_to_marketplace=True` and the destination is a
  recognised marketplace location (`ml-full`, `amazon-fba`), the service invokes
  the connector's `create_inbound_shipment` and stores `external_inbound_id` on
  the transfer.
- `receive_items(transfer_id, lines)` — increments destination stock, advances
  status to PARTIALLY_RECEIVED or RECEIVED.
- `sync_marketplace_listings(transfer_id)` — after a transfer reaches RECEIVED,
  pushes the destination-location quantity into every `MarketplaceListing` for
  the products in the transfer via the connector's `sync_inventory`. Products
  without an existing listing surface as `missing_listings` in the response so
  callers can resolve them manually.

### Automatic inbound reconciliation (ML Full + Amazon FBA)

`services/inbound_shipment_reconciliation.py` is marketplace-agnostic:
its `MARKETPLACE_INBOUND_TARGETS` registry maps a marketplace name to a
`dest_location` filter and connector handle. Two Celery beat
schedules drive it — one per marketplace — so adding a third marketplace
is a registry entry plus a connector implementation of
`get_inbound_shipment_status`.

Active schedules:

| Beat name                          | Cadence       | Calls                              |
| ---------------------------------- | ------------- | ---------------------------------- |
| `mercadolibre-inbound-reconcile`   | 10 past hour  | `reconcile_all_open_ml_inbounds`   |
| `amazon-inbound-reconcile`         | 30 past hour  | `reconcile_all_open_amazon_inbounds` |

Each tick (per marketplace):

1. Finds every `StockTransfer` in `SHIPPED` or `PARTIALLY_RECEIVED` with a
   non-NULL `external_inbound_id` whose `dest_location` matches the target.
2. Calls the marketplace connector's `get_inbound_shipment_status` for each.
3. Resolves the marketplace's per-item rows to local products via a
   two-step lookup: `MarketplaceListing.external_listing_id` first, then
   `Product.sku` fallback. The SKU fallback is critical for Amazon FBA —
   SP-API's inbound items endpoint returns `SellerSKU`, but Amazon
   `MarketplaceListing` rows typically store `ASIN` as the
   `external_listing_id`.
4. Credits stock at the dest location for any positive delta vs. local
   `qty_received`, advances the transfer status, sets `received_at`
   once everything has been received, and bumps `last_reconciled_at`
   so the UI can show "Reconciled X ago".

This means the manual `receive_items` workflow becomes a fallback —
operators only need it when the marketplace hasn't received the
shipment yet or the mapping is incomplete. Marketplace over-reports are
capped at the local `qty_shipped` so a warehouse miscount cannot
inflate Fulcrum stock; the reconciliation never decrements (e.g. if a
marketplace revises a received count downward), so chargebacks and
warehouse corrections still need an explicit operator adjustment.

### Manual reconcile trigger

`POST /api/v1/stock-transfers/{id}/reconcile` runs the same code path
on demand. Surfaced as a "Reconcile inbound now" button on the stock-
transfer detail page when the transfer is in-flight with an external
inbound id. The endpoint returns the per-transfer summary plus the
refreshed transfer row, so the UI can render the new status without a
follow-up GET.

### Pipeline health page

`/marketplaces/health` (under **Marketplaces** in the sidenav) gives
operators a single view of whether the three automatic pipelines
(Amazon order poll, ML order poll, ML+Amazon inbound reconciliation)
are healthy:

| Column          | Source                                              |
| --------------- | --------------------------------------------------- |
| Auth            | `MarketplaceCredential.needs_reauthorization` + `last_refresh_error` |
| Last order poll | `MarketplaceCredential.last_orders_polled_at` (flags stale at 30min) |
| Webhooks (24h)  | most recent `WebhookEvent.received_at` + 24h count for this marketplace. Flags `webhook_likely_disconnected` when the credential is older than 24h AND no events have arrived in 24h |
| Inbound         | rollup of open `StockTransfer`s for this marketplace; stale = `last_reconciled_at` NULL or > 90min |
| Actions         | "Poll orders" + "Reconcile inbound" buttons        |

The buttons run the per-credential entrypoints synchronously, so the
operator gets immediate feedback ("Poll found 3 new orders, 8 line
items"). Both share the same code path as the Celery beat tasks; they
just invoke the per-credential function instead of the bulk runner.

API surface:

| Method | Path                                                      | Notes                          |
| ------ | --------------------------------------------------------- | ------------------------------ |
| GET    | `/api/v1/marketplaces/health/`                            | List rollup, problems first    |
| POST   | `/api/v1/marketplaces/health/{credential_id}/poll-orders` | Synchronous order ingestion    |
| POST   | `/api/v1/marketplaces/health/{credential_id}/reconcile-inbound` | Synchronous inbound poll  |

Both action endpoints embed a refreshed health row in the response so
the UI can patch the table without a follow-up list call.

The webhook column is a defensive complement to the order back-fill
poller. The poller catches missed webhook deliveries automatically, so
silent webhook failures don't lose orders — but they DO mean the
push-notification channel is broken, and a sustained "0 webhooks in
24h" on a credential that's been live for a day is the operator's
signal to re-check the orders subscription in the marketplace's
developer panel. The flag deliberately gates on credential age (only
fires after 24h of connection) to avoid false-positives on a
freshly-connected account.

The REST surface follows the same shape:

| Method | Path                                  | Notes                                                    |
| ------ | ------------------------------------- | -------------------------------------------------------- |
| POST   | `/stock-transfers/`                   | Create draft                                             |
| POST   | `/stock-transfers/{id}/ship`          | Accepts `?push_to_marketplace=true` query flag           |
| POST   | `/stock-transfers/{id}/receive`       | Body: list of `{transfer_item_id, product_id, quantity}` |
| POST   | `/stock-transfers/{id}/sync-listings` | Pushes `available_quantity` to listings via connector    |
| POST   | `/stock-transfers/plan-allocations`   | Bundles flat allocations into one draft per destination  |
| GET    | `/stock-transfers/inventory-snapshot` | Per-product stock by location (feeds the planner UI)     |
| GET    | `/stock-transfers/reconciliation`     | Lines where `qty_received ≠ qty_shipped`                 |

## Security Considerations

- **Token Encryption**: All access and refresh tokens are encrypted at rest
  using AES-256-GCM.
- **Token Refresh**: Tokens are automatically refreshed before expiration.
- **Secure Storage**: Never log or expose tokens in API responses.

---

## Webhooks & Notifications

Fulcrum can receive real-time notifications from marketplaces when orders,
listings, or questions are updated.

### MercadoLibre Webhooks

MercadoLibre pushes notifications to your callback URL when events occur:

1. **Configure your callback URL** in the MercadoLibre Developer Center:
   - Navigate to your application settings.
   - Set the **Notifications callback URL** to:
     `https://your-domain.com/api/v1/webhooks/mercadolibre`
2. **Subscribe to topics** you want to receive:
   - `orders_v2`: Order creation and updates
   - `items`: Listing changes
   - `questions`: Buyer questions
   - `payments`: Payment status changes

MercadoLibre sends JSON payloads like:

```json
{
  "resource": "/orders/1234567890",
  "user_id": 123456789,
  "topic": "orders_v2",
  "application_id": 1234567890123456,
  "attempts": 1,
  "sent": "2025-01-01T12:00:00.000Z"
}
```

### Order back-fill poller (handles dropped webhooks)

MercadoLibre's webhook delivery is best-effort — notifications occasionally
drop or arrive out of order. The `mercadolibre-order-poll` Celery beat
schedule runs every 15 minutes and back-fills any orders the webhook missed:

- `MercadoLibreConnector.fetch_orders` paginates
  `/orders/search?seller=...&order.date_created.from=...` (50 per page,
  capped at 1,000 orders per run).
- The cursor lives on `MarketplaceCredential.last_orders_polled_at` and only
  advances after the credential's run commits, so a transient failure
  re-polls the same range on the next tick.
- Upserts are keyed by `(source=MERCADOLIBRE, external_order_id)` — the
  same key the webhook handler uses. A poll racing the webhook only
  refreshes status/total and never re-decrements stock.
- Per-credential SAVEPOINT isolation: one bad seller's credential cannot
  kill the beat tick for other credentials.

The poller is naturally immune to the multi-tenant credential-selection bug
that affects the webhook path (each credential authenticates with its own
access token), so it's also the recommended workaround for multi-tenant
deployments until per-user webhook URLs land.

### Amazon Notifications

Amazon SP-API uses **Amazon EventBridge** for notifications:

1. **Create an EventBridge destination** in Seller Central.
2. **Configure an API Gateway or Lambda** to receive events.
3. Set up Fulcrum's webhook endpoint as the target:
   `https://your-domain.com/api/v1/webhooks/amazon`

Common notification types:

- `LISTINGS_ITEM_STATUS_CHANGE`: Listing status updates
- `ORDER_CHANGE`: Order created or modified
- `FULFILLMENT_ORDER_STATUS`: FBA fulfillment updates

### Viewing Webhook Events

You can view received webhook events via the API:

```bash
GET /api/v1/webhooks/events
```

---

## Troubleshooting

### Amazon: "Invalid grant" error

- The authorization code expires in 5 minutes. Ensure your callback processes it
  immediately.
- Verify your redirect URI matches exactly (including trailing slashes).

### MercadoLibre: "Invalid client" error

- Double-check your `APP_ID` and `Secret_Key`.
- Ensure your application is activated in the Developer Center.

### MercadoLibre: "Invalid redirect_uri" error

- The redirect URI must match **exactly** what's configured in your app
  settings.
- URL encoding matters—avoid trailing slashes unless configured.
