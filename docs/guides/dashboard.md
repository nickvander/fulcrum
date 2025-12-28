# Dashboard & Business Insights

The Fulcrum Dashboard (nicknamed the "Control Tower") provides a real-time overview of the business operations, inventory health, and procurement pipeline.

## Overview

The dashboard is the default landing page after login. It is designed to prioritize actionable data, showing users exactly where their attention is needed most.

## Key Metrics (KPIs)

### Inventory Availability
- **Definition**: The percentage of products in the catalog that are currently above their low-stock threshold (default is < 5 units).
- **Operational Value**: Indicates how much of the store is "ready to sell." A high percentage means the catalog is well-stocked.

### Inbound Pipeline
- **Definition**: The count of active Purchase Orders (status 'Ordered' or 'Partially Received').
- **Operational Value**: Provides visibility into upcoming stock arrivals. It helps users cross-reference low availability with incoming relief.

### Inventory Value
- **Definition**: The total commercial value of all stock on hand across all products.
- **Calculation**: Sum of (Product Cost Price × Total Quantity On Hand).
- **Operational Value**: Gives financial visibility into the capital tied up in inventory.

### Total Products
- **Definition**: The count of unique product SKUs in the system.

## Critical Low Stock Interface

Below the metrics, the "Critical Low Stock" list displays specific products that have fallen below the availability threshold.
- **Priority**: Products are listed to allow immediate procurement action.
- **Details**: Shows Product Name, SKU, and Current Quantity.

## Technical Implementation

### Widgets
The dashboard is built using a **Widget Architecture**:
- Each metric is an `app-kpi-card` component.
- Widgets are standalone Angular components for maximum modularity.
- Data is fetched reactively via the `DashboardStatsService`.

### DashboardStatsService
- Consolidates data from `ProductService` and `SuppliersService`.
- Implements `forkJoin` to fetch all necessary data in parallel.
- Provides default fallbacks to ensure the dashboard remains functional even if a specific API service is offline.
