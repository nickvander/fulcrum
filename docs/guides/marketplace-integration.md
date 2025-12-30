# Marketplace Integration Guide

This guide covers how to set up and configure integrations with external
marketplaces (Amazon SP-API and MercadoLibre) for Fulcrum.

> **Last Updated**: December 2025

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
