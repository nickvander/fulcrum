# Phase 8: Amazon SP-API Live Integration Testing

## Goal

Implement a robust live integration test suite for Amazon SP-API, mirroring the
success of the MercadoLibre implementation. We will leverage the **Amazon
Dynamic Sandbox** to simulate orders and verify inventory sync without affecting
production data.

## Strategy

### 1. Test Environment: Amazon Dynamic Sandbox

Unlike MercadoLibre which uses "Test Users" in Production, Amazon provides a
dedicated **Sandbox Environment**.

- **Base URL**: `https://sandbox.sellingpartnerapi-na.amazon.com` (for NA
  region).
- **Authentication**: Uses the _same_ LWA (Login with Amazon) credentials but
  directs calls to the Sandbox URL.
- **Capabilities**:
  - **Inventory/Pricing**: Static responses (mostly) but good for verifying
    connection.
  - **Orders**: **Dynamic Sandbox** allows generating fake orders via the
    `Vendor Direct Fulfillment` API or mocking responses for standard orders.
  - **Catalog**: Can retrieve items if they exist in the sandbox catalog (ASIN
    matching).

### 2. Test Suite: `tests/integration/test_amazon_live.py`

We will clone the structure of `test_mercadolibre_live.py` but adapt it for
Amazon's Sandbox constraints.

#### Structure

- **Fixture**: `amazon_sandbox_creds` (Injects Sandbox-specific Refresh Token).
- **Setup**: Configures `MarketplaceCredential` in Fulcrum to point to the
  Sandbox API URL.
- **Components**:
  1.  **Sync Verify**: Push a product update to Amazon Sandbox. Verify 200 OK.
  2.  **Order Mock**: Since we cannot easily "buy" on Amazon Sandbox with a test
      user UI, we will use the **sandbox-only API operations** to _generate_ a
      test order if available, OR we will verify that our `OrderService`
      correctly parses a _simulated_ payload (Verification of the _Reception_
      logic).

## Implementation Plan

### Step 1: Sandbox Configuration

- [ ] Add `AMAZON_SANDBOX` flag to `Marketplace` model (or simple URL override).
- [ ] Update `AmazonConnector` to respect the Sandbox URL when testing.

### Step 2: Test Suite Development

- [ ] Create `backend/tests/integration/test_amazon_live.py`.
- [ ] Implement `test_amazon_sync_lifecycle`.
  - **Action**: Call `AmazonConnector.push_inventory`.
  - **Verify**: Assertion of HTTP 200 from Sandbox.

### Step 3: CI/CD Integration

- [ ] Register new pytest marker: `@pytest.mark.integration_amazon`.
- [ ] Update `scripts/README.md` with instructions for Amazon Sandbox testing.

## Prerequisites

- **Developer**: Must have a valid Amazon Seller Client ID/Secret.
- **Sandbox Account**: Not explicitly required; the Sandbox endpoints accept
  production credentials but return mock data.
