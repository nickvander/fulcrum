# Phase 1: Enhance the Core Product Editor

The goal of this phase is to fix the immediate issues with image handling and
enrich the product information we can store.

1.  **Unify Image Uploads:** Modify the product creation form to allow direct
    image uploads, mirroring the functionality that currently exists in the edit
    form.
2.  **Fix Image Display:** Debug the frontend components to ensure that product
    images are correctly displayed on the product details and list pages.
3.  **Expand Product Details:** Add essential fields to the product model,
    including `cost_price`, `supplier_id`, `width`, `height`, `depth`, `weight`,
    `manufacturer`, `brand`, and `category`. This will involve updating the
    backend database, API, and the frontend forms.

# Phase 2: Implement Intelligent Scanning Workflow

This phase will focus on building the barcode and camera functionalities to
streamline product lookup and creation.

1.  **Decouple Barcode Scanning:** Remove the auto-save behavior from the
    barcode scanner in the "create product" form.
2.  **Implement "Scan-to-Action":** Create a dedicated scanning interface that:
    - Uses the device camera to scan barcodes/QR codes or take a product photo.
    - Searches the database for an existing product.
    - **If found:** Presents options to view the product or update its
      inventory.
    - **If not found:** Redirects to the product creation form, pre-filling the
      barcode.

# Phase 3: Advanced Features and UI/UX Polish

With the core functionality in place, this phase will introduce advanced
customization and improve the user experience.

1.  **Custom Fields:** Implement a system for users to define their own custom
    fields for products, allowing for flexible data management.
2.  **UI Redesign:** Redesign the product list page to be more modern and
    visual, likely using a card-based layout that prominently features the
    product image.
3.  **UX Enhancements:** Add quality-of-life improvements, such as image
    previews before uploading and better feedback during scanning and saving
    operations.
