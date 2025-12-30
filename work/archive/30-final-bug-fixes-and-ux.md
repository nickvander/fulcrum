# Task: Final Bug Fixes and UX Enhancements

## Goal

To resolve all remaining critical bugs in the product management workflow,
enhance the image handling user experience, and ensure all changes are fully
tested and documented.

## Plan

### Phase 1: Fix Critical Routing & Data Saving

1.  **Fix Malformed URLs in `ProductService`:**
    - **Issue:** Adding a trailing slash to the base `apiUrl` caused double
      slashes in sub-route calls (e.g., `products//:id/images`).
    - **Action:**
      1.  Remove the trailing slash from the `apiUrl` in
          `frontend/src/app/products/services/product.ts`.
      2.  Review every method in the service to ensure URLs are constructed
          correctly, fixing the `404 Not Found` errors.

2.  **Fix Custom Field Service Call:**
    - **Issue:** The frontend is calling a non-existent `/api/v1/custom-fields`
      endpoint.
    - **Action:** Correct the `CustomFieldService` to fetch custom field
      _definitions_ from the correct endpoint.

### Phase 2: Enhance Image Handling UX

1.  **Add Image Preview for Staged Images:**
    - **Issue:** Users only see a filename for images selected before saving.
    - **Action:** Modify the `ProductFormComponent` to use `FileReader` to
      display a visual preview of staged images.

2.  **Expand `ProductImage` Model and API:**
    - **Issue:** Images lack a title and description.
    - **Action (Backend):**
      1.  Add `title: str` and `description: str` to the `ProductImage` model
          and schema.
      2.  Generate a new Alembic migration.
    - **Action (Frontend):**
      1.  Update the `ProductImage` interface.
      2.  Add input fields for title and description to the image gallery in the
          `ProductFormComponent`.
      3.  Update the `ProductService` to save this new data.

### Phase 3: Final Polish & Verification

1.  **Ensure Navigation on Save:**
    - **Hypothesis:** This is a side effect of the `404` errors.
    - **Action:** After fixing the routing, re-test the save functionality to
      confirm navigation is restored.

2.  **Documentation Update:**
    - **Action:** Archive the old plan and update `PROGRESS.md`.

3.  **Full Verification:**
    - **Action:** Run all backend and frontend linters and tests.
