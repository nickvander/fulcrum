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
## High Priority (Deferred from Verified UI)
- [x] **Advanced Filter UI**: Re-implemented with debouncing, compact inputs, and non-blocking reload progress bar. ✅
- [x] **Bundle Details Cost**: Display estimated cost in `ProductDetailsDialog`. ✅
- [x] **Avg Cost Logic**: Verified - average cost displays correctly. ✅
- [x] **PO Navigation**: Clicking purchase orders in `ProductDetailsDialog` works. ✅

## Backlog
- [ ] **Credentials**: Valid Amazon SP-API and MercadoLibre credentials for Live Testing (Blocked).
- [x] **Landed Cost Engine**: Logic to distribute PO shipping/tax costs to Product `average_cost`. ✅
- [x] **Expense Management**: Fixed URL bug, added expense types (one-time/recurring), custom categories, KPI widgets. ✅
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
