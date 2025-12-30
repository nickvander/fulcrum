# Task: UX Improvements and API Fixes

## Goal

To resolve the remaining bugs in the product creation workflow, improve the user
experience of the product editor, and establish a clean, modern visual theme for
the application.

## Phase 1: Critical Bug Fixes

1.  **Implement Missing Custom Fields API:**
    - **Issue:** Saving a product results in a "Not Found" error because the API
      for saving custom field values (`/api/v1/products/{id}/custom-fields`)
      does not exist.
    - **Action:**
      1.  Create a new endpoint router in
          `backend/src/api/v1/endpoints/custom_fields.py`.
      2.  Implement the necessary `POST` and `GET` endpoints to handle creating
          and retrieving custom field values for a product.
      3.  Add the new router to the main API router in
          `backend/src/api/v1/api.py`.
      4.  Ensure the corresponding CRUD operations exist and are correct.

2.  **Fix Product Image Rendering:**
    - **Issue:** Uploaded images are not displayed in the "Edit Product" view,
      even though the backend successfully stores them.
    - **Action:**
      1.  Investigate the `ProductFormComponent` (`product-form.ts`) and its
          template (`product-form.html`).
      2.  Debug why the `product.images` array is not being rendered correctly.
          This is likely an issue with the image URL path or the `*ngFor` loop.
      3.  Ensure the `image_path` is correctly resolved to a usable URL for the
          `<img>` tag's `src` attribute.
      4.  Verify the "set as primary" (star icon) functionality.

## Phase 2: UX and Layout Enhancements

1.  **Improve Image Upload Workflow:**
    - **Issue:** The "Upload Images" button is disabled for new products,
      forcing an unintuitive two-step save process.
    - **Action:**
      1.  Modify the `ProductFormComponent` to allow users to select images
          _before_ the initial save.
      2.  Stage the selected `File` objects in the component's state.
      3.  On "Save" for a new product, chain the API calls: first, create the
          product, then use the new `product_id` to upload the staged images.

2.  **Redesign Product Form Layout:**
    - **Issue:** The fields on the "Edit Product" page are poorly organized.
    - **Action:**
      1.  Refactor `product-form.html` to use a more structured layout (e.g.,
          two columns using Flexbox or Angular Material's Grid List).
      2.  Group related fields into sections using `mat-card` components (e.g.,
          "Core Details," "Pricing," "Dimensions," "Custom Fields").

## Phase 3: Theming and Style

1.  **Establish a Cohesive Theme:**
    - **Issue:** The application lacks a consistent and modern visual identity.
    - **Action:**
      1.  Create a `_theme.scss` file in `frontend/src/` to define a new Angular
          Material theme.
      2.  Define a simple color palette with a primary and accent color.
      3.  Import and apply this theme in the main `styles.scss` file.
      4.  Set a clean, modern font (like Inter or Roboto) as the default for the
          application.
