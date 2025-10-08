# Task: Phase 3.5 - Hardening & Feature Completion

## Goal

To solidify the existing features of the application, address all outstanding
`TODO` comments, and ensure the core user workflows are fully functional and
robust. This phase will focus on completing the product CRUD (Create, Read,
Update, Delete) lifecycle and implementing the logic for the intelligent
ingestion features.

## High-Level Approach

We will systematically work through the `TODO` items and incomplete features,
implementing the necessary backend and frontend logic. This involves adding new
methods to the `ProductService`, implementing confirmation dialogs for destructive
actions, and connecting the UI components to the backend API endpoints.

## Implementation Plan

### 1. **Backend: Re-enable Uploads Endpoint**

- **Task:** The `/api/v1/uploads` endpoint was temporarily disabled to resolve a
  persistent startup crash. The root cause of that crash has since been fixed.
- **Action:**
  - In `src/api/v1/api.py`, re-enable the `uploads.router` and its import.
  - Verify in the CI pipeline that the `python-multipart` dependency issue is
    fully resolved.

### 2. **Frontend: Complete Product CRUD Functionality**

- **Task:** The "Add", "Update", and "Delete" functions in the product management
  UI are not fully implemented.
- **Actions:**
  - **Deletion:**
    - In `ProductService`, create a `deleteProduct(id: number)` method that
      sends a `DELETE` request to the API.
    - In `ProductListComponent`, create a confirmation dialog that asks the user
      to confirm the deletion.
    - On confirmation, call the `productService.deleteProduct` method and, upon
      success, remove the product from the `MatTableDataSource`.
  - **Creation & Editing:**
    - In `ProductService`, create `createProduct(product)` and
      `updateProduct(id, product)` methods that send `POST` and `PUT` requests,
      respectively.
    - In `ProductFormComponent`, implement the `onSubmit` method. It should
      check if the form is for a new or existing product and call the
      appropriate service method.
    - On success, navigate the user back to the product list page.

### 3. **Frontend: Implement Photo Ingestion Workflow**

- **Task:** The "Take Photo" button in the `ProductIngestionComponent` captures an
  image but does not upload it or process the result.
- **Actions:**
  - In `ProductService`, create an `uploadImage(file: Blob)` method that sends
    the image data as `FormData` to the `/api/v1/uploads/` endpoint.
  - In `ProductService`, create an `identifyProductFromImage(imageUrl: string)`
    method that calls the `/api/v1/ai/identify-from-image` endpoint.
  - In `ProductIngestionComponent`, update the `capturePhoto` method to:
    1.  Call `productService.uploadImage`.
    2.  On success, take the returned `file_path` and call
        `productService.identifyProductFromImage`.
    3.  Use the returned product data to pre-fill a new product form.

### 4. **Frontend: Address Remaining `TODO`s**

- **Task:** Clean up miscellaneous `TODO` comments.
- **Actions:**
  - **`ProductService`:** Replace the hardcoded API URL with a value from an
    environment variable.
  - **`SettingsComponent`:** Implement the `onSubmit` and data loading logic.
  - **`AiSearchBarComponent`:** The voice search is a larger feature; we will
    leave this `TODO` for a future phase but acknowledge it.

## Validation

- All backend and frontend tests must pass in the CI pipeline.
- Manually verify all completed user stories:
  - A user can successfully create a new product using the form.
  - A user can edit an existing product.
  - A user can delete a product after confirming the action in a dialog.
  - A user can take a photo, have it uploaded, and see mock data returned from
    the AI service.
