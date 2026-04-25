# Task: MercadoLibre Deep Integration & UI Polishing

## Goal

To finalize the MercadoLibre marketplace integration with deep data
synchronization (multiple images, promotional pricing, stock locations) and
refine the product details UI for a premium multi-channel experience.

## Critique of Previous State

1.  **Limited Sync:** Only the primary image and the "regular" price were being
    synchronized, missing active promotions and additional media.
2.  **UI Clutter:** Product details displayed all images in a simple grid that
    became crowded with many photos.
3.  **Missing Context:** No clear indication of original vs. discounted prices
    in the hero section or marketplace chips.
4.  **Stock Gaps:** Marketplace inventory wasn't being tracked proactively in
    Fulcrum's location-based inventory system.

## Implementation Plan

1.  **Advanced MercadoLibre Connector:**
    - Updated `mercadolibre.py` to utilize the `/prices` endpoint for
      source-of-truth pricing data.
    - Implemented parallel fetching using `asyncio.gather` for batch item
      updates.
    - Added support for fetching and processing the full image array for each
      item.

2.  **Marketplace Listing Service Enhancements:**
    - Modified `import_marketplace_listings` to handle multi-image
      synchronization and automatic product shell creation.
    - Added proactive stock synchronization with MercadoLibre location mapping.
    - Integrated promotional data fields (`original_price`,
      `discount_percentage`) into the sync workflow.

3.  **Premium Frontend UI:**
    - **Image Gallery:** Replaced the grid layout with a scrollable thumbnail
      strip and a large primary preview.
    - **Full-Screen Preview:** Created a new standalone
      `ImagePreviewDialogComponent` with smooth transitions.
    - **Dynamic Pricing:** Updated the Hero section to show the final discounted
      price as the primary value when a promotion is active.
    - **Marketplace Deep Links:** Updated marketplace chips to link directly to
      the external store page.

## Validation

- **Backend Tests:** 196 tests passing, including mocked integration tests for
  the listing service.
- **Frontend Tests:** 334 tests passing across 78 test files.
- **Linter:** `ruff` check passing on backend; frontend code formatted and
  linted.
- **Manual Audit:** Verified specific product (ID 93) displays correct
  promotional pricing and high-res image gallery.
