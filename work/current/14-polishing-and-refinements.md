# Task: Phase 3.6 - Polishing & Refinements

## Goal

To improve the user experience and complete the remaining functionality for the product module before moving on to the next major phase. This plan addresses the polishing items identified after the completion of Phase 3.5.

## Implementation Plan

### 1. **Implement Reactive Search**

-   **Task:** Connect the AI search bar to the reactive product list.
-   **Critique:** The `onSearchQuery` method in `ProductListComponent` is currently a placeholder and does not filter the product list.
-   **Actions:**
    -   Create a new `searchProducts` method in the `ProductService` that takes a query string, calls the `/api/v1/products/search` endpoint, and updates the `_products` BehaviorSubject with the results.
    -   In `ProductListComponent`, update the `onSearchQuery` method to call this new service method.
    -   Add a "Clear Search" button to the UI that calls the original `getProducts` method to restore the full list.

### 2. **Enhance Image Management**

-   **Task:** Allow users to delete product images and set a primary image.
-   **Critique:** Users can currently upload images but cannot manage them further.
-   **Backend Actions:**
    -   Create a new endpoint, `DELETE /api/v1/products/{product_id}/images/{image_id}`, to delete a `ProductImage` record and its corresponding file.
    -   Create a new endpoint, `POST /api/v1/products/{product_id}/images/{image_id}/set-primary`, to set the `is_primary` flag on a specific image and unset it on all others for that product.
-   **Frontend Actions:**
    -   In `ProductFormComponent`, add a "Delete" and "Set as Primary" button overlay to each image in the gallery.
    -   Implement the corresponding `deleteProductImage` and `setPrimaryProductImage` methods in the `ProductService`.
    -   Call these methods from the `ProductFormComponent` and refresh the product data on success.

### 3. **Introduce Optimistic UI Updates (Optional Stretch Goal)**

-   **Task:** Make the UI feel faster by updating the state before the API call completes.
-   **Critique:** The UI currently waits for API confirmation, which can feel slow on a poor connection.
-   **Actions:**
    -   Refactor the `createProduct`, `updateProduct`, and `deleteProduct` methods in `ProductService`.
    -   Immediately update the `_products` BehaviorSubject with the expected new state.
    -   In the `subscribe` block of the API call, if an error occurs, revert the state change and show an error notification to the user. This provides a snappy UI experience while maintaining data integrity.

## Validation

-   All existing and new tests must pass in the CI pipeline.
-   The product list should filter correctly when a search query is entered.
-   Users can successfully delete a product image.
-   Users can successfully set a product image as primary.
-   (Optional) The UI should reflect changes immediately for CRUD operations.
