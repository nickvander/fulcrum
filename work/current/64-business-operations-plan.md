# Business Operations & Merchant Dashboard Plan

This plan outlines the evolution of Fulcrum from a marketplace integrator into a comprehensive "Business Operating System" for merchants.

## Goal
To empower merchants to manage their entire operation—inventory, costs, expenses, marketing, and sales channels—from a single, premium dashboard.

## Phase 9: Business Operations Core

### 1. Cost & Expense Management (Enhanced)
Go beyond simple "Price - Cost".
- **Advanced COGS**: Implement FIFO/LIFO logic for inventory valuation.
- **Landed Cost Calculation**: Distribute shipping/tax from POs across items to update `average_cost`.
- **Operating Expenses**: Track non-COGS expenses (Ads, Software, Rent) to calculate *Net Profit*.
- **Profitability Analytics**: "Real-time P&L" per SKU and overall.

### 2. Advanced Inventory (Bundles & Assemblies)
- **Product Bundles (Kitting)**:
    - Virtual products composed of other SKUs (e.g., "Gift Set").
    - Inventory calculated dynamically: `min(component_stock)`.
    - Auto-deduct components when bundle releases.
- **Manufacturing/Assembly**:
    - Work Orders to "build" stock from raw materials.

### 3. Integrated Marketing & Campaigns
- **Marketing Calendar**: A visual drag-and-drop calendar for planning Ad events, Email blasts, and Sales.
- **Campaign Manager**:
    - Entities linked to Products ("Boost this item during this week").
    - Tracking: Generate UTM links for social media.
    - ROI: Attribute sales to campaigns via referrer/UTM.
- **"Smart Boost"**: Recommendations on what to promote based on:
    - High Stock + Low Velocity (Clearance)
    - High Margin + High Velocity (Star Products)

### 4. Deep Supplier Integration
- **Supplier Portal / Links**: Store portal URLs and credentials.
- **Supplier Products**: Manage "Their SKU" vs "Our SKU" mapping (`supplier_product.py` exists, needs UI).
- **Restock Intelligence**: "Time to Reorder" alerts based on Lead Time + Sales Velocity.

## Implementation Roadmap

### Step 1: Inventory & Cost Engine
- Update `Product` model for Bundle support (recursive relationship).
- Build `Expense` model.
- Implement "Landed Cost" distribution logic in `PurchaseOrder` service.

### Step 2: Supplier & Restock
- Build UI for `SupplierProduct` mapping.
- Implement "Days of Inventory" calculation.

### Step 3: Marketing Operations
- Build `Campaign` and `CampaignEvent` models.
- Create "Marketing Calendar" UI (Angular).
- Implement "Smart Boost" logic.

## Future / Deferred
- **1st Party Storefront**: Deferred for security/focus.
- **Ad Platform Integration**: Direct API connections to Meta/Google Ads.

## Glossary of Terms
- **COGS (Cost of Goods Sold)**: Direct costs attributable to the production of the goods sold in a company.
- **FIFO (First-In, First-Out)**: Inventory valuation method where assets produced or acquired first are sold first.
- **LIFO (Last-In, First-Out)**: Inventory valuation where the most recently produced items are sold first.
- **PO (Purchase Order)**: A commercial document issued by a buyer to a seller indicating types, quantities, and prices for products.
- **SKU (Stock Keeping Unit)**: A scannable bar code, most often seen printed on product labels in a retail store.
- **UTM (Urchin Tracking Module)**: Variants of URL parameters used by marketers to track the effectiveness of online marketing campaigns.
- **1P (First-Party)**: Direct sales from the merchant to the consumer (e.g., via their own storefront), as opposed to 3P (Third-Party) marketplace sales.

## Engineering Strategy: Internationalization (i18n)
To support multi-lingual interfaces efficiently, we will adopt the following strategy:

1.  **Token-Based Labels**: Avoid hardcoding strings. Use semantic keys (e.g., `AUTH.LOGIN_BUTTON` instead of "Login").
2.  **Library Selection**: We will use **@angular/localize** (Native) or **Transloco** (Flexible).
    - *Recommendation*: **Transloco** is often preferred for rapid development as it uses simple JSON files per language and allows hot-swapping languages without rebuilding the app.
3.  **Validation Messages**: Backend validation errors should return error *codes*, not text. The frontend transforms codes into localized messages.
