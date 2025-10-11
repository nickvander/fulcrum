# Task: Final Bug Fixes and Polish

## Goal

To resolve all remaining critical bugs in the product management workflow, ensure data is displayed correctly, and update the project documentation.

## Plan

### Phase 1: Critical Backend Routing Fixes

1.  **Fix `405 Method Not Allowed` on DELETE:**
    *   **Action:** Add the missing `DELETE /{product_id}` endpoint to the `products.py` API router.

2.  **Fix `404 Not Found` on Custom Fields & Redirects:**
    *   **Action:** Add a trailing slash to the `apiUrl` in the frontend `ProductService` to match the backend's routing and eliminate the `307` redirects that are breaking sub-routes.

### Phase 2: Frontend Data and Display Correction

1.  **Fix Image Display on Product List:**
    *   **Action:** Update the backend `Product` Pydantic schema to ensure the `images` relationship is always included in the API response.

2.  **Fix Photo Ingestion `[Object Object]` Error:**
    *   **Action:** Correct the data handling in the `ProductIngestionComponent` and `ProductFormComponent` to ensure the product data from the AI service is correctly parsed and patched into the form.

### Phase 3: Documentation

1.  **Action:** Archive the old plan (`28-ux-and-api-fixes.md`).
2.  **Action:** Create this new plan file (`30-final-bug-fixes.md`).
3.  **Action:** Update `work/current/PROGRESS.md` with a summary of the completed work and the new plan.
