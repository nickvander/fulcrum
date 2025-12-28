# Phase 7: Deep Marketplace Integration

This phase transitions from architectural stubs to live, production-ready marketplace integrations for Amazon SP-API and MercadoLibre. The primary focus is on secure credential management, automated product mapping, and robust OAuth lifecycle handling.

## 🎯 Objectives
- **Secure Storage**: Implement an encrypted vault for marketplace API credentials and tokens.
- **Product Mapping**: Establish a mapping service to link internal products to marketplace-specific identifiers (ASIN, ML-ID).
- **Live Connectors**: Replace stubs with functional API clients for Amazon and MercadoLibre.
- **Automated Sync**: Implement real-time inventory and pricing synchronization via Celery workers.
- **Webhook Registry**: Set up listener endpoints for marketplace events (e.g., new orders).

## 📊 Tracks & Steps

### Track 1: Secure Credential Management
- [x] **Step 1: Encryption Layer**
    - Implement a wrapping service using `cryptography` for AES-256-GCM encryption of sensitive tokens.
    - Store encrypted credentials in a new `MarketplaceCredential` database table.
- [x] **Step 2: Credential Management API**
    - Create endpoints for securely saving/updating credentials without exposing secrets in logs or responses.

### Track 2: Product Mapping & Catalog Sync
- [x] **Step 3: Identity Management Service**
    - Build a service to manage `MarketplaceListing` correlations.
    - Implement "Auto-Mapping" logic based on SKU matching.
- [x] **Step 4: Bulk Listing Import**
    - Implement a "Fetch Existing Listings" tool to import products already present on marketplaces into Fulcrum.

### Track 3: Live Amazon SP-API Integration
- [x] **Step 5: OAuth Flow**
    - Implement the full Amazon OAuth2 flow (LWA - Login with Amazon).
    - Automate token refresh cycles in the background.
- [x] **Step 6: Inventory & Price Feeds**
    - Implement `sync_inventory` using Amazon's Listings API.
    - Implement price updates and status monitoring.

### Track 4: Live MercadoLibre Integration
- [x] **Step 7: OAuth & Refresh**
    - Implement MercadoLibre OAuth flow.
    - Handle token expiration and persistent connection management.
- [x] **Step 8: Listing Operations**
    - Implement publishing and inventory updates for ML.

### Track 5: Event-Driven Architecture
- [x] **Step 9: Webhook Integration**
    - Set up endpoints to receive notifications from Amazon and MercadoLibre.
    - Implement a dispatcher to trigger internal inventory adjustments on external sales.

## 🛠️ Verification Plan
- **Integration Tests**: Mock API responses using `responses` or `vcrpy` for connector logic.
- **Security Audit**: Verify that credentials are never stored in plaintext and are redacted from all logging pipelines.
- **Load Testing**: Simulate bulk inventory updates across 100+ listings to verify Celery worker performance.
