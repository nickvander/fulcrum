# Product Image Workflow Enhancement Plan

## Objective
Update the product image workflow to allow temporary image deletion and improve overall UX by implementing proper save/revert functionality and custom field support.

## Current Issues
1. When editing a product and deleting an image, the user is taken straight back to the product screen instead of allowing temporary changes
2. The save button is not greyed out when there are no active changes
3. Custom fields are not properly integrated in the product create/edit workflow
4. Image deletion should be temporary until the user clicks save
5. After save, the user should be taken back to the product list

## Requirements

### 1. Temporary Image Deletion
- When a user deletes an image, it should only be marked as deleted temporarily
- The image should remain until the user clicks "Save" 
- The "Save" button should become enabled when an image deletion occurs
- Only after clicking "Save" should the image be permanently deleted and user redirected to product list

### 2. Save Button State Management
- Implement state tracking to monitor if there are any active changes
- Grey out the save button when there are no changes
- Enable the save button when any changes are made:
  - Image additions
  - Image deletions
  - Changes to primary image selection
  - Changes to product information
  - Changes to custom fields

### 3. Custom Fields Integration
- Add custom fields to the product create/edit form
- Allow users to add/edit custom fields when creating or editing a product
- Save custom fields along with the product data
- Display custom fields appropriately in the form

### 4. Navigation Flow
- When user clicks "Save" after making changes, redirect to product list
- When user clicks "Cancel" or "Back" without saving, discard temporary changes and return to product list
- Preserve the current form state until explicit save or cancel action

## Implementation Steps

### Phase 1: State Management
1. Update product form component to track changes state
2. Implement a changes detection mechanism that monitors:
   - Image changes (additions, deletions, primary selection)
   - Product data changes
   - Custom field changes
3. Bind save button disabled/enabled state to the changes detection
4. Add a discard changes confirmation when navigating away without saving

### Phase 2: Image Deletion Workflow
1. Modify image deletion logic to mark images as "deleted" temporarily instead of immediately removing
2. Add a mechanism to track which images are marked for deletion
3. Update the save functionality to process "marked for deletion" images permanently
4. Update the UI to show visual indication of images pending deletion

### Phase 3: Custom Fields Integration
1. Add custom fields section to the product form
2. Implement dynamic custom field addition/removal
3. Update form validation to include custom fields
4. Update the save API call to include custom field data

### Phase 4: Navigation Logic
1. Update the save button behavior to navigate to product list after successful save
2. Implement proper cancel/discard functionality
3. Add confirmation dialog for leaving without saving
4. Test the complete navigation flow

## Technical Considerations
- Update the product form component state management
- Modify image service to handle temporary deletion
- Update API calls to handle batch operations (save product + delete images + custom fields)
- Consider using Angular Reactive Forms for better state management
- Ensure proper error handling in case of save failures
- Add appropriate loading states during save operations

## Testing Requirements
- Unit tests for state management logic
- E2E tests for the complete image workflow
- Test for save button enable/disable functionality
- Test for custom field integration
- Test for proper navigation after save/cancel
- Test for handling of failures and error states
