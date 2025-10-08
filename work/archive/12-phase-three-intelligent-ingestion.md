# Task: Phase 3 - Intelligent Product Ingestion & Indexing

## Goal

To automate product creation by integrating camera and barcode scanning
capabilities into the PWA. This will streamline the product ingestion process,
allowing users to add new products quickly by scanning a barcode or taking a
photo of the item.

## High-Level Approach

This phase involves both backend and frontend development. On the backend, we
will create new API endpoints to handle file uploads and AI-powered image
analysis. We will also ensure that our semantic search index is automatically
updated whenever a product is created or modified. On the frontend, we will
create a new `ProductIngestionComponent` that utilizes a `HardwareService` to
access the device's camera. This component will integrate with a third-party
scanning library (`ngx-scanner`) to detect barcodes and will also allow users to
capture and upload photos for analysis.

## Backend Implementation Plan

1.  **Verify & Harden Product Indexing:**
    - Review the existing `create_product` and `update_product` endpoints in
      `src/api/v1/endpoints/products.py`.
    - Confirm that the `generate_product_embedding.delay()` Celery task is
      correctly called on both product creation and update to keep the search
      index fresh.
    - Add this check to the existing tests if it's not already present.

2.  **Implement File Upload Endpoint:**
    - Create a new endpoint `POST /api/v1/uploads/generate-presigned-url`.
    - This endpoint will generate a pre-signed URL for uploading files directly
      to a storage provider (e.g., a local directory for now, but designed for
      S3, etc., in the future). This avoids large file transfers through the API
      server.
    - For this phase, we'll simulate this by creating a simple file upload
      handler that saves the file locally. We will need a new `uploads` router.

3.  **Implement AI Image Analysis Endpoint:**
    - Create a new endpoint `POST /api/v1/ai/identify-from-image`.
    - This endpoint will take an image URL (or file path) as input.
    - It will use the `AIService` to analyze the image and return structured
      data about the identified product (e.g., name, description).
    - For now, the `DummyAIService` will be updated to return mock data for a
      sample image.

## Frontend Implementation Plan

1.  **Create `HardwareService`:**
    - In `frontend/src/app/core/services/`, create a new `hardware.service.ts`.
    - This service will wrap the `navigator.mediaDevices` browser API to provide
      methods for requesting camera access and capturing images.
    - `getCameraStream()`: Returns a `MediaStream` for the video feed.
    - `captureImage(stream)`: Captures a still frame from a `MediaStream`.

2.  **Integrate `ngx-scanner`:**
    - Install the `ngx-scanner` library: `npm install ngx-scanner`.
    - Create a new `ProductIngestionModule` and a `ProductIngestionComponent`.
    - In the component's template, use the `<ngx-scanner>` element.
    - Use the `HardwareService` to get the camera stream for the scanner.
    - Implement a handler for the `(scan)` event to process detected barcode
      data.

3.  **Implement Photo Ingestion Flow:**
    - Add a "Take Photo" button to the `ProductIngestionComponent`.
    - On click, use the `HardwareService` to capture an image.
    - Upload the captured image to the backend using the new file upload
      endpoint.
    - After a successful upload, send the image URL to the
      `/ai/identify-from-image` endpoint.
    - Populate the product form with the data returned from the AI service.

4.  **Update Routing:**
    - Add a new route for the `ProductIngestionComponent` in the main
      application routing.
    - Add a "New Product" button in the `ProductListComponent` that navigates
      to this new ingestion page.

## Validation

- Backend: New unit tests will be created for the upload and AI analysis
  endpoints.
- Frontend: New component tests will be created for the `HardwareService` and
  `ProductIngestionComponent`.
- End-to-end: Manually verify the full flow: scan a barcode -> fetch product
  data (mocked) -> pre-fill form. And take a photo -> upload -> analyze (mocked)
  -> pre-fill form.
