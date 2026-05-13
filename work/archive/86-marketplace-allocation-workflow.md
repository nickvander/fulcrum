# 86: Marketplace Allocation Workflow

Implements the gap between PO receiving and marketplace stock sync. PO
receiving still updates Fulcrum internal inventory only — marketplace
quantities are now allocated through an explicit, auditable transfer
workflow.

## Mode

Mexico focus → **MercadoLibre Full** is the primary fulfillment model.
Amazon FBA is structurally identical and supported through the same
plumbing. FBM (ship-from-own-warehouse) is deferred until the storefront
exists.

## Slices Delivered

### Slice 1 — Internal stock-transfer foundation (commit `b4823c8`)

- `StockTransfer` / `StockTransferItem` models, alembic migration
  `a1b2c3d4e5f6`.
- State machine: DRAFT → SHIPPED → PARTIALLY_RECEIVED → RECEIVED, +
  CANCELLED.
- Service: `create_draft`, `update_draft`, `ship`, `receive_items`,
  `cancel`, `delete_draft`. Ship validates source-location stock and
  decrements it via `InventoryAdjustment` audit rows; receive increments
  the destination location.
- Endpoints under `/api/v1/stock-transfers/`.
- Frontend: list / detail / create-dialog / receive-dialog under
  `frontend/src/app/marketplaces/stock-transfers/`. Sidenav collapses
  marketplaces into an expansion panel exposing Channels + Stock
  Transfers.
- Location convention: free-form string on `inventory_items.location`
  (`default`, `ml-full`, `amazon-fba`). Table promotion deferred.

### Slice 2 — MercadoLibre Full API integration (commit `84708b3`)

- `BaseMarketplaceConnector.create_inbound_shipment` /
  `get_inbound_shipment_status` (default no-op stubs for non-ML
  connectors).
- `MercadoLibreConnector` real implementations with deterministic stub
  fallback when no token is present — dev / test envs run end-to-end
  without live ML calls.
- `StockTransferService.ship(push_to_marketplace=True)` reserves an
  inbound shipment with the marketplace and stores `external_inbound_id`.
- `StockTransferService.sync_marketplace_listings` pushes the
  destination-location quantity into every `MarketplaceListing` for the
  products in the transfer. Listings without an `external_listing_id`
  are reported as "missing" so the user can resolve them.
- `marketplace_listings.available_quantity` column (migration
  `b2c3d4e5f6a7`).
- Frontend: "Ship + reserve inbound" action on marketplace destinations,
  "Push qty to listings" on received transfers, sync-result panel
  showing per-listing outcome and missing-listing warning.

### Slice 3 — Allocation planner + reconciliation (commit `6e94b2d`)

- `GET /stock-transfers/inventory-snapshot` — per-product stock by
  location, feeds the planner.
- `POST /stock-transfers/plan-allocations` — bundles a flat list of
  `{product_id, dest_location, qty_planned}` into one DRAFT transfer
  per destination, with overcommit validation.
- `GET /stock-transfers/reconciliation` — items where
  `qty_received != qty_shipped` (shrinkage, damage, over-receipt).
- Frontend planner page: every product with internal / ML / Amazon
  quantities and per-row "send to ML" / "send to Amazon" inputs.
  Submitting creates one draft per destination.
- Frontend reconciliation page: shrinkage table with delta colouring and
  links back to each transfer.

## Verification

- **Backend**: 38 tests
  (`tests/test_stock_transfers_api.py`,
   `tests/test_stock_transfer_planner_api.py`,
   `tests/services/test_stock_transfer_service.py`,
   `tests/services/test_stock_transfer_marketplace.py`,
   `tests/services/test_stock_transfer_planner.py`,
   `tests/services/test_ml_inbound_shipment.py`).
- **Frontend**: 35 vitest specs across the 7 stock-transfer files.
- **Production build** (`ng build`): green for all three slices.
- **Dev-server smoke (Slice 1)**: full create → ship → receive cycle
  verified through the Angular dev proxy. Inventory ended up at the
  expected default / ml-full split.

## Open follow-ups

- Live MercadoLibre Full inbound API path is implemented but only
  exercised against the stub fallback. First time the user has a real
  ML token and pushes a real shipment, watch the request/response for
  field-name differences ("inbound_shipments" path and key names from
  ML's docs may need adjusting).
- A webhook for ML's "inbound received" event would close the loop so
  receiving doesn't need to be entered manually. Currently received-qty
  is captured via the receive dialog.
- Promoting `inventory_items.location` from string to a real
  `stock_locations` table becomes worthwhile once multiple internal
  warehouses appear.
- UI was not driven through a real Chrome session — no browser was
  connected to the Claude in Chrome MCP. Backend + dev-proxy + unit
  tests all green; a human eye on the planner / reconciliation /
  detail pages before launch is still recommended.
