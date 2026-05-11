# 82: Purchase Order Receiving to Inventory Workflow

## Goal

Make supplier purchase documents, especially Alibaba PDFs and images, become
reviewable purchase orders and then reliable stock movements in product
inventory.

## Current State

- Text-based PDFs, HTML, and TXT supplier documents can be parsed by the
  traditional PO ingestion service without AI keys.
- Scanned PDFs and image files need AI/OCR. Without configured AI keys, the UX
  should fail clearly instead of creating an empty purchase order.
- The purchase order editor has a unified document drop zone that can create
  PO lines or match a document against an existing PO.
- Receiving updates product inventory and weighted/last purchase cost.

## Improvements Made

- Import PO dialog now uses the unified parser and accepts PDF, JPG, PNG, AVIF,
  HTML, and TXT.
- Empty scanned documents now return a clear "needs AI/OCR" error instead of an
  empty extraction.
- Invoice match review can receive matched quantities directly into inventory.
- Receiving now targets exact PO item IDs and variants, not only product IDs.
- Variant IDs are preserved when creating or updating PO items.
- Invoice "apply values" now updates the correct form controls.
- Attached invoice list now displays backend fields that actually exist.
- Successfully parsed documents on existing POs are attached to the PO record.
- Supplier product names from imported documents are sent through PO creation so
  future imports can match Alibaba names better.

## Best Next Features

1. Add a dedicated receiving review screen after document parsing:
   matched item, extracted quantity, already received, proposed receive quantity,
   destination location, and discrepancy warning in one table.
2. Add OCR fallback for scanned PDFs/images when cloud AI is not configured.
   Tesseract or another local OCR path would cover the no-API-key workflow.
3. Persist original supplier document metadata:
   original filename, source vendor, parsed JSON, confidence, and user-approved
   corrections.
4. Add a supplier alias/mapping review queue:
   "Alibaba item name -> Fulcrum product/variant" with confidence and reuse.
5. Add marketplace allocation planning, not automatic sync from receiving:
   receiving must update Fulcrum internal inventory only. MercadoLibre/Amazon
   quantities are decided later through a separate marketplace allocation
   workflow because sellable marketplace quantity is not necessarily warehouse
   quantity.

## UX Principle

Receiving should always be a review-and-confirm action. The system can propose
stock updates from a PDF/image, but users should see what will change before
internal inventory changes.

## Marketplace Inventory Boundary

Do not queue MercadoLibre or Amazon stock updates as a side effect of receiving
purchase order items. Marketplace availability is a separate business decision:
users may reserve inventory, split quantities by channel, hold back damaged or
unlisted stock, or decide not to expose newly received stock immediately.
