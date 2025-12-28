# Phase 6: Marketplace Integration & Dashboard Widgets

## Goal
To transform Fulcrum from a passive inventory tracker into an active "Control Tower" that provides actionable insights via a customizable dashboard and connects deeply with external sales channels (Amazon, MercadoLibre).

## Strategy
We will split this phase into two parallel tracks:
1.  **Immediate Value (Widgets)**: Build the frontend `Dashboard` and "Widgets" system to give users a home screen with vital stats.
2.  **Deep Integration (Marketplaces)**: Plan and research the complex authentication and API requirements for Amazon and MercadoLibre, laying the groundwork for the integration.

## Key Deliverables

### 1. Dashboard & Widgets (Frontend)
-   **Dashboard Framework**: A grid-based layout (using `css-grid` or a library like `angular-gridster2` if needed, but CSS Grid is preferred for simplicity) that hosts dynamic widgets.
-   **Widget Registry**: A service to manage available widgets and user preferences (which widgets are visible, order).
-   **Core Widgets**:
    -   **KPI Card**: Shows a single metric (e.g., "Total Sales", "Pending Orders") with a trend arrow.
    -   **Recent Activty**: List of recent POs or Sales.
    -   **Low Stock Alert**: Warning list of items below reorder point.

### 2. Marketplace Integration (Backend/Planning)
-   **Architecture**:
    -   `MarketplaceConnector` (Abstract Base Class): Defines `authorize()`, `publish_listing()`, `sync_stock()`, `fetch_orders()`.
    -   `MercadoLibreConnector`: Implements OAuth2 and listing publication.
    -   `AmazonConnector`: Implements SP-API signature version 4 and listing APIs.
-   **Authentication Flow**:
    -   **Oauth Helper**: A generic endpoint `/marketplaces/authorize/{name}` that redirects to the marketplace.
    -   **Callback Handler**: `/marketplaces/callback/{name}` to handle secrets and store `MarketplaceCredentials`.
-   **Sandbox/Testing Strategy**:
    -   **MercadoLibre**: Use official `test_user` endpoint to simulate buyers/sellers.
    -   **Amazon**: Use the SP-API **Sandbox endpoints** (e.g., `sandbox.sellingpartnerapi-na.amazon.com`).

### 3. Marketplace Dashboard Widgets (Future)
-   **Sales by Channel**: Pie chart showing Fulcrum vs Amazon vs MercadoLibre.
-   **Listing Status**: Bar chart showing Active/Pending/Error listings.

## Detailed Tasks

### Track 1: Dashboard
-   [ ] Create `DashboardModule` (lazy-loaded at `/dashboard`).
-   [ ] Implement `DashboardComponent` with a 3-column / 4-row grid.
-   [ ] Create `Widget` interface and `WidgetHost` directive.
-   [ ] Build `KpiWidgetComponent`.
-   [ ] Build `RecentOrdersWidgetComponent`.

### Track 2: Marketplace Planning
-   [ ] Read Amazon SP-API docs (Developer Guide).
-   [ ] Read MercadoLibre API docs (Test Accounts).
-   [ ] Create `docs/guides/marketplace-setup.md`.

## Verification
-   **Dashboard**:
    -   Unit tests for Widget interactions.
    -   Visual verification of responsiveness (mobile/desktop).
-   **Marketplace**:
    -   Successful "Hello World" API call to a sandbox (if possible) or at least a documented curl command that *would* work with valid keys.
