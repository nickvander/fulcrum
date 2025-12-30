# Task: Enhance Product Image Management UX

## Goals

1.  Improve the usability and visual clarity of the image management interface
    in the product editor.
2.  Position action icons consistently in the top-right corner of each image.
3.  Add a confirmation step for deleting images to prevent accidental data loss.
4.  Provide clearer visual feedback for the primary image selection.

## Plan

### Phase 1: Refactor Image Actions & UI

1.  **Relocate Action Buttons:**
    - Modify the CSS in `product-form.scss` to create an overlay for action
      buttons on each image.
    - Position the buttons in the top-right corner of the image thumbnails in
      `product-form.html`.

2.  **Enhance "Set Primary" UX:**
    - Update the `setPrimaryImage` button icon to dynamically switch between
      `star` (is primary) and `star_border` (is not primary).
    - Add a `matTooltip` to the button to clarify its function (e.g., "Set as
      primary image").

3.  **Visually Mark Primary Image:**
    - Apply a distinct CSS class or style (e.g., a colored border or an overlay
      badge) to the `mat-card` or `img` element for the image that is marked as
      primary.

### Phase 2: Implement Deletion Confirmation

1.  **Integrate Confirmation Dialog:**
    - In the `deleteImage` method in `product-form.ts`, use the `MatDialog`
      service to open the app's standard `ConfirmationDialog`.

2.  **Configure Dialog:**
    - Pass a clear and concise title and message to the dialog, such as "Delete
      Image?" and "Are you sure you want to delete this image? This action
      cannot be undone."

3.  **Handle Confirmation:**
    - Modify the `deleteImage` method to only proceed with calling the
      `productService.deleteProductImage` method if the user confirms the action
      in the dialog.

### Phase 3: Verification

1.  **Manual Testing:**
    - Thoroughly test the updated UI in the browser to confirm:
      - Buttons are correctly positioned and styled.
      - The primary image is clearly marked, and the star icon updates
        correctly.
      - The delete confirmation dialog appears and functions as expected.
      - All existing image functionality (zoom, edit details) remains intact.

2.  **Automated Testing:**
    - Run the full frontend test suite to ensure that the changes have not
      introduced any regressions.
