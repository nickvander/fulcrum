# Plan: UI & UX Refinements (Phase 2)

> **Goal:** Polish the product list and details UI for mobile responsiveness, consistent branding, and improved data visibility.

## 1. Product Details Dialog
- [x] **Marketplace Deduplication**: Ensure only one badge per marketplace type (Amazon, eBay, etc.) is displayed.
- [x] **Barcode Cleanup**: Remove barcode from key stats as it's duplicated in "Labels & Codes".
- [x] **SKU Styling**: Make SKU smaller (`0.75rem monospace`) and less prominent.
- [x] **Create Bundle Button**: Standardize color to Material Pink (`#E91E63`) to match branding.
- [x] **Stat Pills**: Reduce font sizes for a more compact, refined look.

## 2. Product List (Grid/List)
- [x] **Phone Selection Bar**: 
    - Fix overflow by reducing padding (`2px` side padding) and gap.
    - Implement ultra-compact layout for mobile.
    - Ensure "Create Bundle" button is Pink (`#E91E63`).
- [x] **Action Icons**: 
    - Smartly display icons based on screen size.
    - Mobile: Show all 3 icons (Dashboard, Add, Scan) directly without hamburger.
    - Desktop: Show desktop-specific actions.
- [x] **Marketplace Deduplication**: Apply same deduplication logic to list/grid view badges.
- [x] **Stock Status Colors**: 
    - **Green** (>10): In Stock
    - **Orange** (1-10): Low Stock
    - **Red** (0): Out of Stock
- [x] **Visual Fixes**: 
    - Fix Infinite Scroll FAB icon visibility in light mode.
    - Fix Grid View hamburger menu visibility on touch devices.

## 3. Technical Debt
- [x] **SCSS Fixes**: Resolve syntax errors (extra closing braces) and missing classes.
- [x] **Refactoring**: Extract `getUniqueListings()` helper for reusability.
