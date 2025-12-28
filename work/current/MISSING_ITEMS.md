# Missing Items & Roadmap

## ✅ Completed Phases

- **Phase 6: Marketplaces & Widgets** - Complete
- **Phase 7: Deep Marketplace Integration** - Complete
  - Encrypted Credential Management (AES-256-GCM)
  - Real-time Product Mapping (SKU-based auto-mapping)
  - Full OAuth Token Refresh Cycle (Amazon SP-API, MercadoLibre)
  - Settings UI for multi-account management

## 🚀 Upcoming Phases

- [ ] **Phase 8: Advanced Analytics**
  - **Track 1: Data Aggregation**
    - [ ] ETL pipeline to normalize sales data from all channels (Internal, Amazon, MercadoLibre).
    - [ ] Profitability calculation (Revenue - COGS - Marketplace Fees - Shipping).
## High Priority (Phase 8 & 9)
- [ ] **Credentials**: Valid Amazon SP-API and MercadoLibre credentials for Live Testing (Blocked).
- [ ] **Landed Cost Engine**: Logic to distribute PO shipping/tax costs to Product `average_cost`.
- [ ] **Inventory Bundles**: Database models and logic for "Virtual Products" (Kits/Sets).
- [ ] **Expense Management**: Data models for non-COGS business expenses.
- [ ] **Marketing Calendar**: UI for scheduling and visualizing campaigns.

## Medium Priority
- [ ] **Supplier Portal**: Dedicated metadata for Suppliers (Logins, Portals).
- [ ] **1P Storefront**: Public-facing checkout (Deferred).
  - **Track 2: Dashboard Visualization**
    - [ ] "Command Center" dashboard with real-time sales velocity.
    - [ ] Inventory forecasting widgets (Days of Supply, Reorder Recommendations).
  - **Track 3: Reporting Engine**
    - [ ] Exportable CSV/PDF reports (P&L, Tax Summary).
    - [ ] Multi-channel performance comparison.
