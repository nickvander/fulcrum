# Task: Products Page UX & Functionality Overhaul

## Goal

To resolve critical bugs on the Products page, implement missing core functionality, and introduce significant UI/UX enhancements for a more modern, intuitive, and efficient user experience. All new features must be implemented in a modular, test-driven fashion.

## Critique of Current State

1.  **Broken Core Functionality:** The "Delete Product" button is non-functional. The "Adjust Stock" feature, a cornerstone of inventory management, is completely missing.
2.  **Inefficient Workflows:** Common actions like adjusting stock or making a quick edit require navigating away from the main list, adding unnecessary clicks and friction.

## Implementation Plan

This plan is divided into three phases, starting with critical fixes and progressing to a complete redesign and feature enhancement. **Each new piece of functionality must be accompanied by corresponding unit tests.**

---

### Phase 1: Critical Bug Fixes & Core Functionality

The first priority is to ensure all fundamental product management actions are working correctly and are fully tested.

1.  **Fix Product Deletion:**
    *   **Backend:** Systematically review and test the `DELETE /api/v1/products/{product_id}` endpoint.
    *   **Frontend:** Debug the `deleteProduct` method in the `ProductService`. Sometimes it deletes products and other times it shows a 500 error from the frontend
    *   **Testing:** Write a new frontend unit test to confirm that calling `deleteProduct` successfully removes a product from the list and that a confirmation dialog is shown.

2.  **Implement "Adjust Stock" Functionality:**
    *   **Backend:**
        *   Create a new SQLAlchemy model, `InventoryAdjustment`, to provide a clear audit trail.
        *   Create a new, fully tested endpoint, `POST /api/v1/products/{product_id}/adjust-stock`.
    *   **Frontend (Modular Approach):**
        *   Create a new, standalone `AdjustStockDialogComponent` in a shared module.
        *   Add an "Adjust Stock" button to the `ProductListComponent`.
        *   Implement the `adjustStock` method in the `ProductService`.
    *   **Testing:** Write unit tests for the `AdjustStockDialogComponent` to verify its form and submission logic.

---

### Phase 2: UI/UX Redesign

With the core functionality stable, the focus shifts to modernizing the user interface.

1.  **Implement "Quick Edit" Side Panel:**
    *   **Goal:** Allow users to edit products without leaving the context of the list view.
    *   **Action (Modular Approach):**
        *   The main `ProductsComponent` will manage a `MatSidenav` container.
        *   Clicking the "Edit" button on a product card will open the side panel.
        *   The `ProductFormComponent` will be loaded into the side panel's content area.
        *   A new "Close" button on the form will close the panel and refresh the product list if changes were made.
    *   **Testing:** Write tests to verify that the side panel opens with the correct product data and closes as expected.

---

### Phase 3: Advanced Features & Workflow Polish

The final phase will introduce advanced features that dramatically improve workflow efficiency.

1.  **Introduce Batch Actions:**
    *   **Goal:** Allow users to modify multiple products at once.
    *   **Action (Modular Approach):**
        *   Create a new `BatchActionToolbarComponent` that appears when one or more products are selected.
        *   Add checkboxes to each product card.
        *   Implement batch operations like "Delete Selected" in the `ProductService`.
    *   **Testing:** Write unit tests for the `BatchActionToolbarComponent` and the batch methods in the `ProductService`.

## Validation

- All existing and new backend and frontend tests must pass.
- The "Delete," "Adjust Stock," and "Quick Edit" functionalities must be fully operational and covered by tests.
- The new card-based layout must be responsive and visually polished.
