# Marketplace Credential Setup Guide

This guide provides step-by-step instructions for obtaining the necessary API
credentials for Amazon SP-API and MercadoLibre implementation.

> **Status (Dec 2025)**: Both platforms require verified seller accounts to
> access their APIs.

## 1. Amazon SP-API (Selling Partner API)

There are two main paths to obtain API credentials. Choose the one that fits
your budget and testing needs.

### Option A: Private Seller (Best for Internal Use)

**Cost**: $39.99/month (Professional Seller Account) **Pros**: Simpler
registration flow for internal apps ("Private Developer"). **Cons**: Monthly
fee.

1.  **Register**: Go to
    [Amazon Seller Central](https://sellercentral.amazon.com/) and register for
    a **Professional Selling Plan**.
2.  **Verify**: Complete the identity verification (ID upload + Video Call).
3.  **App Registration**:
    - Go to **Partner Network > Develop Apps**.
    - Click **Register as a developer**.
    - Select "My organization sells on Amazon" (Private Developer).
    - Create a new App to get `client_id` and `client_secret`.

### Option B: Solution Provider (Best for Free Sandbox)

**Cost**: Free **Pros**: Access to SP-API Sandbox without a monthly
subscription. **Cons**: Registration flow allows for "Public" apps (intended for
3rd party tools), but works for sandbox testing. Still requires **Full Identity
Validation**.

1.  **Register**: Go to the
    [Solution Provider Portal](https://sellercentral.amazon.com/developer/register).
2.  **Verify**: You must still provide business info and identity documents (ID,
    Bank Statement).
3.  **App Registration**:
    - Create a profile.
    - Create an App intended for "Public" use (you don't need to list it
      publicly).
    - This grants access to the **Sandbox** environment credentials.

### Step 3: Get LWA Credentials (Both Options)

Once your app is created (Private or Public):

1.  Copy your **LWA Client ID** and **LWA Client Secret**.
2.  Save these as `AMAZON_CLIENT_ID` and `AMAZON_CLIENT_SECRET`.

### Step 4: Generate a Refresh Token (Self-Authorization)

For server-to-server apps acting as _yourself_:

1.  In the **Develop Apps** table, click the arrow next to "Edit App" and select
    **Authorize**.
2.  This creates a "Self Authorization" flow (or generates a refresh token
    directly for private apps).
3.  Save the **Refresh Token** as `AMAZON_REFRESH_TOKEN`.

---

## 2. MercadoLibre (Mexico)

MercadoLibre requires **Strict Identity Validation** before you can create an
App. Without an App, you cannot generate the credentials needed to create Test
Users. There is **no workaround** for this initial step.

### Prerequisites

- **Real MercadoLibre Account**: Use your personal or business account.
- **Identity Validation (The Main Blocker)**:
  - You must verify your identity by uploading a **Government ID** (INE/IFE) and
    taking a **Selfie**.
  - Go to **My Account > Privacy** or visit the
    [Developer Panel](https://developers.mercadolibre.com.mx/devcenter/) to
    trigger the check.
  - _Note_: You **cannot** proceed to create an App until this is green-lit.

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
