# Marketplace Credential Setup Guide

This guide provides step-by-step instructions for obtaining the necessary API
credentials for Amazon SP-API and MercadoLibre implementation.

> **Status (Dec 2025)**: Both platforms require verified seller accounts to
> access their APIs.

## 1. Amazon SP-API (Selling Partner API)

To generate valid `client_id`, `client_secret`, and `refresh_token` for testing,
you must register as a "Private Developer".

### Prerequisites

- **Amazon Seller Central Account**: You likely need a **Professional Seller**
  plan ($39.99/mo) to initially register as a developer, though policies are
  relaxing in 2026.
  - _Tip_: If you only have a Buyer account, you must register as a Seller at
    [sell.amazon.com](https://sell.amazon.com/).
- **Identity Verification**: Amazon will require business/tax info and identity
  verification (video call or ID upload).

### Step 1: Register as a Developer

1. Log in to [Amazon Seller Central](https://sellercentral.amazon.com/).
2. Navigate to **Partner Network** > **Develop Apps**.
3. Click **Register as a developer**.
4. Fill in your contact info.
5. **Data Access**: select "My organization sells on Amazon" (Private
   Developer).
   - This is simpler than Public Developer and requires less auditing for basic
     features.

### Step 2: Create a Private App

1. Once approved (can take 24h+), go back to **Develop Apps**.
2. Click **+ Add new app client**.
3. App Name: `Fulcrum Test` (or similar).
4. API Type: **SP-API**.
5. **Redirect URI**: `http://localhost:4200/marketplaces/amazon/callback`
   (Important for OAuth flow).
   - Even if using headless script, set a valid localhost URL.
6. Click **Save and Exit**.

### Step 3: Get LWA Credentials

1. You will see your **LWA Client ID** and **LWA Client Secret**.
2. Save these safe. These match `AMAZON_CLIENT_ID` and `AMAZON_CLIENT_SECRET`.

### Step 4: Generate a Refresh Token (Self-Authorization)

For server-to-server apps (like ours) acting as _yourself_, you can
self-authorize to get a long-lived Refresh Token without the UI flow.

1. In the **Develop Apps** table, click the arrow next to "Edit App" and select
   **Authorize**.
2. This creates a "Self Authorization" flow.
3. It will generate a **Refresh Token**.
4. Save this as `AMAZON_REFRESH_TOKEN`.

---

## 2. MercadoLibre (Mexico)

MercadoLibre requires **Identity Validation** before allowing app creation. You
can use an infinite "Test User" for _some_ things, but to Create an App (to get
Client ID), you need a real account.

### Prerequisites

- **Real MercadoLibre Account**: Can be an old one or new.
- **Identity Validation**: Mandatory. You must upload front/back of ID and take
  a selfie.
  - Go to **My Account** > **Privacy** or try ensuring your "Seller" profile is
    active.
  - If you are blocked from creating an app, it will tell you "Validate
    Identity".

### Step 1: Create the App

1. Go to the
   [MercadoLibre DevCenter](https://developers.mercadolibre.com.mx/devcenter/).
2. Log in with your real account.
3. Click **Create new application**.
4. **Name**: `Fulcrum Integration`
5. **Short Name**: `fulruminteg`
6. **Redirect URI**: `http://localhost:4200/marketplaces/mercadolibre/callback`
   - Must verify HTTPS vs HTTP policies. Localhost is usually allowed.
7. **Scopes**: Select "Read/Write" or "Offline Access" (offline_access is
   crucial for refresh tokens).
8. Save.

### Step 2: Get Credentials

1. You will get an **App ID** (Client ID) and **Secret Key** (Client Secret).
2. Save these as `ML_CLIENT_ID` and `ML_CLIENT_SECRET`.

### Step 3: Generate Token for Testing

Unlike Amazon, there is no "Self-Authorize" button. You must perform the OAuth
flow once.

1. Construct URL:
   `https://auth.mercadolibre.com.mx/authorization?response_type=code&client_id={YOUR_APP_ID}&redirect_uri={YOUR_REDIRECT}`
2. Paste in browser, log in.
3. It redirects to `localhost:4200...?code=TG-...`.
4. Copy the `code`.
5. Use `setup_mercadolibre_test.py` or `curl` to exchange `code` for
   `access_token` and `refresh_token`.

```bash
curl -X POST \
-H "accept: application/json" \
-H "content-type: application/x-www-form-urlencoded" \
"https://api.mercadolibre.com/oauth/token" \
-d "grant_type=authorization_code" \
-d "client_id={YOUR_APP_ID}" \
-d "client_secret={YOUR_SECRET}" \
-d "code={THE_CODE}" \
-d "redirect_uri={YOUR_REDIRECT}"
```

6. Save the `refresh_token` for your system to use.
