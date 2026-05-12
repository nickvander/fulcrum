# Dashboard & Business Insights

The Fulcrum Dashboard (nicknamed the "Control Tower") provides a real-time
overview of the business operations, inventory health, and procurement pipeline.

## Overview

The dashboard is the default landing page after login. It is designed to
prioritize actionable data, showing users exactly where their attention is
needed most.

## Key Metrics (KPIs)

### Inventory Availability

- **Definition**: The percentage of products in the catalog that are currently
  above their low-stock threshold (default is < 5 units).
- **Operational Value**: Indicates how much of the store is "ready to sell." A
  high percentage means the catalog is well-stocked.

### Inbound Pipeline

- **Definition**: The count of active Purchase Orders (status 'Ordered' or
  'Partially Received').
- **Operational Value**: Provides visibility into upcoming stock arrivals. It
  helps users cross-reference low availability with incoming relief.

### Inventory Value

- **Definition**: The total commercial value of all stock on hand across all
  products.
- **Calculation**: Sum of (Product Cost Price × Total Quantity On Hand).
- **Operational Value**: Gives financial visibility into the capital tied up in
  inventory.

### Total Products

- **Definition**: The count of unique product SKUs in the system.

## Critical Low Stock Interface

Below the metrics, the "Critical Low Stock" list displays specific products that
have fallen below the availability threshold.

- **Priority**: Products are listed to allow immediate procurement action.
- **Details**: Shows Product Name, SKU, and Current Quantity.

## Launch Readiness

The dashboard includes a launch-readiness panel for customer onboarding and
go-live checks. It summarizes required setup, inventory movement, pending
supplier document imports, marketplace connection status, and demo data.

### Demo Data Guardrail

When the optional demo workspace has been created, the readiness panel lists
each detected demo record before go-live, including the demo store marker,
supplier, product, purchase order, inventory receipt, supplier-product link, and
learned alias records.

The **Clean up demo data** action removes only records that still match the
Fulcrum demo fingerprints. Cleanup is automatically blocked when those records
appear to have customer activity, such as non-demo purchase orders, sales,
marketplace listings, expenses, custom product setup, supplier document import
reviews, or learned aliases outside the demo mapping. When cleanup is blocked,
the panel shows the reason so the user can review the affected records manually.

## Technical Implementation

### Widgets

The dashboard is built using a **Widget Architecture**:

- Each metric is an `app-kpi-card` component.
- Widgets are standalone Angular components for maximum modularity.
- Data is fetched reactively via the `DashboardStatsService`.

### Inventory Health Widget

- **Purpose**: A dedicated "Act Now" list for inventory managers.
- **Logic**: Flags items that are critical based on:
  - **Low Quantity**: < Global Threshold (default 10) OR Per-Product Custom
    Threshold.
  - **Low Days of Inventory**: < 30 Days (calculated based on sales velocity).
- **Actions**:
  - **Status Indicators**: Explicit text ("Low Quantity: 5 units" or "12 Days
    Left").
  - **Fast Add**: "Add to Cart" button immediately adds the item to your active
    drafted Purchase Order (or creates a new one).

### DashboardStatsService

- Consolidates data from `ProductService` and `SuppliersService`.
- Implements `forkJoin` to fetch all necessary data in parallel.
- Provides default fallbacks to ensure the dashboard remains functional even if
  a specific API service is offline.
