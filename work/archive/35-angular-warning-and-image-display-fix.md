# Task: Fix Angular Compiler Warning & Product Image Display Issue

## Goals

1. Address the Angular compiler warning for ImageDialogComponent being unused
2. Fix the issue where images are not displaying properly on the main product
   page
3. Implement a long-term solution for handling dynamically opened components

## Identified Issues

### Issue 1: Angular Compiler Warning

- **Problem**: NG8113 warning:
  `ImageDialogComponent is not used within the template of ProductForm`
- **Cause**: The ImageDialogComponent is imported in ProductForm for
  programmatic usage via MatDialog.open(), but Angular's template compiler does
  not recognize this as "use" since the component isn't directly in the template
- **Current State**: Functionality works but shows a warning in the build

### Issue 2: Product Image Display Not Working

- **Problem**: Images are not displaying on the main product page despite
  implementation
- **Potential Causes**:
  - Image path resolution issues
  - Backend image serving configuration
  - Data not properly populated in the product model
  - Error handling in the getPrimaryImage method

## Plan

### Phase 1: Investigate and Fix Product Image Display Issue

1.  **Debug Image Path Resolution:**
    - Verify that image paths are being retrieved correctly from the backend
    - Check if the getImageUrl method is properly formatting URLs
    - Add logging to getPrimaryImage method to see what path is being calculated
    - Test error handling in onImageError method

2.  **Check Backend Image Serving:**
    - Verify that images are stored correctly on the backend
    - Confirm that the '/uploads/' endpoint is working properly
    - Test if the image files exist at expected locations

3.  **Validate Product Data:**
    - Check if product.images and product.primary_image fields are being
      populated correctly
    - Debug the structure of the data coming from the ProductService
    - Ensure image objects have the correct properties (image_path, is_primary,
      etc.)

### Phase 2: Address Angular Compiler Warning

1.  **Research Solutions:**
    - Investigate Angular's approach to handling dynamically opened components
    - Review Angular documentation on standalone components and MatDialog
    - Look into app configuration options for registering components globally

2.  **Implement Proper Solution:**
    - Option A: Add ImageDialogComponent to the Application Configuration
    - Option B: Create an AppComponents module to register all standalone
      components
    - Option C: Use a different approach for dynamic component loading if needed

### Phase 3: Long-term Architecture Improvements

1.  **Refactor Component Architecture:**
    - Establish a consistent pattern for dynamically opened components
    - Create a shared service for dialog management if needed
    - Document the approach for future developers

2.  **Testing:**
    - Verify the solution resolves the compiler warning
    - Ensure all existing functionality continues to work
    - Add tests for the new architecture if applicable

## Concerns

1.  The Angular standalone component + MatDialog integration is a known area
    with limitations in the current Angular ecosystem
2.  Changing architecture may require updates to multiple components
3.  The image display issue might be related to backend configuration or data
    structure
4.  Changes to app-level configuration should be done carefully to avoid
    breaking other functionality
