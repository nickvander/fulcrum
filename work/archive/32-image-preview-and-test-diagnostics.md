# Task: Image Preview Fix & Frontend Test Diagnostics

## Goal

To resolve the final outstanding bug in the product image workflow and to
systematically diagnose and resolve the persistent timeout issue in the frontend
test suite.

## Plan

### Phase 1: Fix Product Image Previews

The immediate goal is to fix the image preview functionality in the "Edit
Product" view. While creating products with images now works, the images do not
display when editing an existing product.

1.  **Diagnose the 404 Error:**
    - **Hypothesis:** The frontend is constructing the correct URL
      (`/uploads/product_images/...`), but the backend is still not serving the
      file correctly, resulting in a `404 Not Found` error. This is likely due
      to the complexities of the broad volume mount (`./backend:/app`) and how
      FastAPI serves static files from within that structure.
    - **Action:**
      1.  Run the application and use your browser's developer tools to confirm
          the exact URL that is returning a 404.
      2.  Verify that the image file exists in the
          `backend/uploads/product_images` directory on your local machine after
          uploading.
      3.  Review the `main.py` file and the FastAPI documentation for
          `StaticFiles` to ensure the `directory` parameter is correctly
          configured to work with the current volume mount setup. It may need to
          be an absolute path like `/app/uploads`.

2.  **Implement the Fix:**
    - **Action:** Based on the diagnosis, apply the necessary correction. This
      will likely involve either adjusting the `StaticFiles` mount point in
      `main.py` or correcting the `getImageUrl` function in `product-form.ts` if
      the URL path is unexpectedly different.

### Phase 2: Diagnose Frontend Test Timeout in `product-form.spec.js`

This phase follows a "divide and conquer" strategy to isolate the root cause of
the test timeout, which has resisted standard troubleshooting methods.

1.  **Isolate the Problem via Template Simplification:**
    - **Action:** Systematically comment out sections of
      `frontend/src/app/products/components/product-form/product-form.html`.
    - **Methodology:**
      1.  Start by commenting out the entire `<div class="form-columns">`
          section. If the test passes (even if it fails on logic), the problem
          is within the form.
      2.  If so, uncomment the first column and re-run. Then comment it out and
          uncomment the second column. This will isolate the issue to one of the
          two main layout columns.
      3.  Continue this process, commenting out individual `mat-card` sections,
          then individual `mat-form-field` elements, until you find the single
          element whose presence causes the test to hang. The image gallery
          (`<div class="image-gallery">`) with its `*ngFor` loop is a prime
          suspect.

2.  **Enable Interactive Debugging:**
    - **Action:** Launch the test runner in debug mode.
    - **Methodology:**
      1.  Modify the `test` script in `frontend/package.json` to add the
          `--debug` flag to the `wtr` command: `"test": "ng test -- --debug"`.
      2.  When you run `npm test --prefix frontend`, the runner will provide a
          URL. Open this URL in a Chromium-based browser.
      3.  The tests will be paused. Open the browser's developer tools (`F12`)
          and use the console and element inspector to look for errors or
          strange behavior. You can set breakpoints and step through the code.
