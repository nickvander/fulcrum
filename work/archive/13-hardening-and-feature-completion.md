# Task: Phase 3.5 - Hardening, Refinement & Feature Completion

## Goal

To solidify the existing features of the application, address all outstanding
`TODO` comments, and improve the overall code quality and user experience. This
phase will focus on completing the product CRUD lifecycle, implementing the
photo ingestion workflow, and introducing key refinements like user feedback and
centralized state management.

## Critique of Current Implementation

1.  **Poor User Feedback:** The application provides no visual feedback for
    asynchronous operations. When a user creates, updates, or deletes a
    product, the UI doesn't show a loading indicator or a success/error
    notification. This makes the application feel unresponsive and confusing.
2.  **Lack of Centralized State Management:** The `ProductListComponent` fetches
    the list of products once. After a creation, update, or deletion, it will
    not automatically reflect the changes. The component would need to manually
    refetch the data, which is inefficient and not reactive.
3.  **Incomplete Error Handling:** While the backend has some error handling, the
    frontend does not. If an API call fails, the error is only logged to the
    console, leaving the user without any indication of what went wrong.
4.  **Missing Confirmation Dialogs:** Destructive actions, like deleting a
    product, are not protected by a confirmation dialog. This is a significant
    UX flaw that could lead to accidental data loss.
5.  **Configuration Management:** The frontend `ProductService` has a hardcoded
    API URL, which is not a good practice. This should be managed via Angular's
    standard environment configuration.
6.  **Technical Debt:** The backend `uploads` endpoint is still disabled due to
    the CI environment issues we worked around. This needs to be properly fixed
    and re-enabled.

## Updated Implementation Plan

### 1. **UX & User Feedback Refinements**

- **Task:** Implement a global loading indicator and notification system.
- **Actions:**
  - Create a `LoadingService` that can be used to show/hide a global spinner.
  - Create an `HttpInterceptor` that automatically shows the spinner at the
    start of any API request and hides it upon completion.
  - Integrate the Angular Material `MatSnackBar` module to create a
    `NotificationService` that can be used to display success and error
    messages to the user.

### 2. **State Management & Reactivity**

- **Task:** Refactor the `ProductService` to act as a centralized store for
  product data.
- **Actions:**
  - In `ProductService`, introduce a `BehaviorSubject` to hold the list of
    products.
  - Create a public `products$` observable that components can subscribe to.
  - Modify the `getProducts`, `createProduct`, `updateProduct`, and
    `deleteProduct` methods to update the `BehaviorSubject` after each
    operation. This will ensure that any component subscribed to `products$`
    will automatically and reactively update its view.

### 3. **Complete Product CRUD Functionality**

- **Task:** Fully implement the create, update, and delete workflows.
- **Actions:**
  - **Deletion:**
    - Create a `ConfirmationDialogComponent` in the `SharedModule`.
    - In `ProductListComponent`, use the `MatDialog` service to open this
      component before deleting a product.
    - On confirmation, call the `productService.deleteProduct` method and show a
      success/error notification. The UI will update automatically due to the
      new reactive state management.
  - **Creation & Editing:**
    - Implement the `createProduct` and `updateProduct` methods in
      `ProductService`.
    - In `ProductFormComponent`, implement the `onSubmit` method to call the
      appropriate service function.
    - On success, show a notification and navigate back to the product list.

### 4. **Implement Photo Ingestion Workflow**

- **Task:** Connect the "Take Photo" feature to the backend.
- **Actions:**
  - **Backend:** Re-enable the `/api/v1/uploads` endpoint in `api.py` and ensure
    the `python-multipart` dependency is correctly installed in the CI
    environment.
  - **Frontend:**
    - Implement the `uploadImage` and `identifyProductFromImage` methods in
      `ProductService`.
    - In `ProductIngestionComponent`, chain these service calls in the
      `capturePhoto` method.
    - On success, navigate to the "Add Product" form, pre-filling the fields
      with the data returned from the AI service.

### 5. **Implement Product Image Uploads**

- **Task:** Allow users to upload and manage images for each product.
- **Backend Actions:**
  - Create a new SQLAlchemy model, `ProductImage`, with fields for `id`,
    `product_id`, `image_path`, and `is_primary`.
  - Generate a new Alembic migration to create the `product_images` table in
    the database.
  - Create a new endpoint, `POST /api/v1/products/{product_id}/images`, that
    handles the file upload, saves the image, and creates a corresponding
    `ProductImage` record.
  - Update the main `GET /api/v1/products/{product_id}` endpoint to include a
    list of associated images in its response.
- **Frontend Actions:**
  - In `ProductFormComponent`, add a new section for image management.
  - Include a file input (`<input type="file">`) to allow users to select
    images.
  - On image selection, call a new `productService.uploadProductImage` method.
  - Display the uploaded images in a simple gallery or list within the form,
    with an option to set one as the primary image.

### 6. **Configuration and Final `TODO`s**

- **Task:** Clean up remaining technical debt.
- **Actions:**
  - **Frontend:** Move the hardcoded API URL in `ProductService` to the
    `environment.ts` file.
  - **Settings Page:** Briefly implement the save/load logic for the settings
    page to remove the `TODO`s.

## Validation

- All backend and frontend tests must pass in the CI pipeline.
- The application must feel responsive, with loading indicators for all API
  calls and clear success/error notifications for all user actions.
- The product list must update automatically after any CRUD operation.
- A user can successfully upload one or more images to a product.
- The full photo ingestion flow must be functional end-to-end.
- A user can successfully create, update, and delete a product.
