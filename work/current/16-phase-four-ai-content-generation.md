# Task: Phase 4 - AI Content Generation & Media Management

## Goal

To integrate AI-powered content generation into the product management workflow, enabling users to automatically create compelling marketing copy and manage associated media assets. This phase will focus on building the backend infrastructure and frontend components necessary to generate product descriptions and manage images.

## Implementation Plan

### 1. **Backend: AI Content Generation**

-   **Task:** Create a new endpoint to generate a product description using an AI model.
-   **Actions:**
    -   Create a new endpoint, `POST /api/v1/ai/generate-description`, that accepts a product's name and key features as input.
    -   Integrate with a third-party AI service (e.g., OpenAI's GPT) to generate a marketing-focused product description.
    -   The endpoint should return the generated text.

### 2. **Frontend: AI-Powered Description Generation**

-   **Task:** Add a feature to the `ProductFormComponent` that allows users to automatically generate a product description.
-   **Actions:**
    -   Add a "Generate with AI" button next to the description field in the `ProductFormComponent`.
    -   When clicked, this button will call the new `/api/v1/ai/generate-description` endpoint, using the product's name and other relevant fields as input.
    -   The generated description will then be populated into the description field, allowing the user to review and edit it before saving.

### 3. **Backend: Advanced Media Management**

-   **Task:** Enhance the backend to support more advanced media management features.
-   **Actions:**
    -   Add an `order` field to the `ProductImage` model to allow for custom sorting of images.
    -   Create a new endpoint, `POST /api/v1/products/{product_id}/images/reorder`, that accepts a list of image IDs in the desired order.
    -   Update the `GET /api/v1/products/{product_id}` endpoint to return images in the specified order.

### 4. **Frontend: Drag-and-Drop Image Sorting**

-   **Task:** Implement a drag-and-drop interface for reordering product images.
-   **Actions:**
    -   Integrate the Angular CDK's drag-and-drop module into the `ProductFormComponent`'s image gallery.
    -   Allow users to reorder images by dragging and dropping them.
    -   When the user drops an image into a new position, call the new `/api/v1/products/{product_id}/images/reorder` endpoint to save the new order.

## Validation

-   All backend and frontend tests must pass.
-   A user can successfully generate a product description using the "Generate with AI" feature.
-   A user can successfully reorder product images using a drag-and-drop interface.
-   The new image order is correctly persisted and reflected in the product details.
