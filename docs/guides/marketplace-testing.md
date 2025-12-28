# Marketplace Integration Testing Guide

This guide details how to verify marketplace integrations, specifically MercadoLibre, using test users in a production environment.

## MercadoLibre Testing

MercadoLibre does not provide a separate sandbox environment. Instead, it allows the creation of "Test Users" that exist in the production environment but are flagged for testing. These users can buy and sell from each other without incurring fees or affecting reputation.

> [!WARNING]
> Test users operate in the **Production** environment. Always ensure you are using the correct credentials. Test items should be clearly marked (e.g., "Test Item - Do Not Buy").

### 1. Creating Test Users

We have provided a utility script to automate the creation of test users. You will need a valid **Access Token** from your real developer account (or a production account) to create these test users.

**Script Location:** `scripts/setup_mercadolibre_test.py`

#### Prerequisites
- A valid MercadoLibre Access Token (from your Developer Portal application).
- Python 3 installed.

#### Usage

**Create a Marketplace User (Buyer/Seller in a specific country, e.g., Mexico):**
```bash
python scripts/setup_mercadolibre_test.py --token $ML_ACCESS_TOKEN --type local --site MLM
```

**Create a Global Selling User (CBT - Cross Border Trade):**
```bash
python scripts/setup_mercadolibre_test.py --token $ML_ACCESS_TOKEN --type global --country US
```

**Output:**
The script will output JSON credentials. **Save these immediately**, as they cannot be retrieved later.
```json
{
  "id": 12345678,
  "nickname": "TESTUSER123",
  "password": "secure_password",
  "email": "test_user_123@testuser.com"
}
```

### 2. Testing Scenarios

Use these test users to verify "Live" features without cost.

| Feature | Test Strategy |
| :--- | :--- |
| **Product Sync** | Connect the "Seller" test user to Fulcrum. Publish a product. Verify it appears on ML with "Test Item" in the title. |
| **Stock Updates** | Change stock in Fulcrum. Verify the listing on ML updates its quantity. |
| **Purchase Orders** | Login to ML with a second test user ("Buyer"). Buy the item. Verify Fulcrum receives the order webhook. |
| **Shipping** | Use "Test Labels" provided by ML (if available) or simulate status changes via API. |

### 3. Switching to Production

To switch from "Testing" with test users to real "Production" selling:

1.  **Deactivate Test Mode in Fulcrum**:
    - Currently, Fulcrum treats all credentials equally. "Production" simply means using your real business account credentials instead of the test user credentials.
2.  **Update Credentials**:
    - Go to **Marketplace Settings** in Fulcrum.
    - Connect your **Real Business Account** (do not use the test user credentials).
3.  **Verify Settings**:
    - Ensure your synchronization settings (e.g., "Auto-Publish") are configured correctly for a live environment.

### 4. UI Verification

To verify the integration "In action" via the Fulcrum UI:

1.  **Generate Test Users**: Run `setup_mercadolibre_test.py` and save the credentials (email/password).
2.  **Add Credentials**: Go to `http://localhost:4200/marketplaces/settings/mercadolibre` and input the *App Credentials* (Client ID/Secret) corresponding to the app that owns the test user.
    *   *Note*: Test users are "users", not "apps", but you authenticate *as* them using your app's flow.
3.  **Sync**: Trigger a sync from the Fulcrum UI.
4.  **Verify on ML**:
    - Log in to [MercadoLibre (Global Selling or Local Site)](https://www.mercadolibre.com/jms/cbt/lgz/login) using the **Test User Email and Password**.
    - Check "My Listings" to see the items pushed from Fulcrum.

## Amazon SP-API Testing

Amazon provides a dedicated Sandbox environment.
- **Endpoint**: Connect to the Amazon Sandbox API endpoint tailored for your region.
- **Credentials**: Use your IAM User credentials authorized for the Sandbox.
- **Workflow**: Create a "Sandbox" marketplace in Fulcrum and toggle the "Is Sandbox" flag (if implemented) or simply use the Sandbox API URL during setup.

## Troubleshooting

- **"Invalid Token"**: Your developer access token has expired. Refresh it in the ML Developer Portal.
- **"User not found"**: Test users are deleted after 60 days of inactivity. Create a new one.
