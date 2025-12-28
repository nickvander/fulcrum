# Task: AI Invoice Processing

## Goal

Implement AI-powered invoice parsing to streamline the Purchase Order workflow.
When a supplier invoice (PDF/Image) is uploaded, the system will automatically
extract line items, amounts, and match them against the corresponding PO.

## Prerequisites

- Phase 5 Supplier & PO Management (complete)
- LLM API integration (OpenAI, Anthropic, or Google)

## Implementation Plan

### 1. Backend: Invoice Parser Service

- **File:** `backend/src/services/invoice_parser_service.py`
- **Actions:**
  - Accept PDF or image file upload
  - Use LLM vision API to extract structured data:
    - Vendor name, invoice number, date
    - Line items: description, quantity, unit price, total
  - Return structured JSON response
  - Store raw extraction results in `SupplierInvoice` table

### 2. Backend: Invoice Matching Endpoint

- **File:** `backend/src/api/v1/endpoints/purchase_orders.py`
- **Actions:**
  - `POST /api/v1/purchase-orders/{po_id}/invoices/upload`
  - Parse uploaded invoice using InvoiceParserService
  - Match extracted line items against PO items
  - Return match results with confidence scores
  - Create `SupplierInvoiceItem` records linked to PO items

### 3. Frontend: Invoice Upload Component

- **File:** `frontend/src/app/suppliers/invoice-upload/`
- **Actions:**
  - Drag-and-drop file upload area
  - PDF/Image preview
  - Loading state during AI processing
  - Display extracted data in editable table
  - "Confirm Match" button to finalize

### 4. Frontend: 3-Way Matching View

- **File:** `frontend/src/app/suppliers/purchase-orders/po-matching/`
- **Actions:**
  - Side-by-side comparison: PO vs Invoice vs Receipt
  - Highlight discrepancies (price, quantity)
  - Allow manual override/correction
  - Approval workflow for discrepancies

## Configuration

- **Settings Toggle:** Enable/disable AI invoice parsing
- **API Key Storage:** Secure credentials in environment variables
- **Fallback:** Manual entry if AI unavailable

## Validation

- [ ] Invoice upload successfully extracts line items
- [ ] Matching algorithm correctly links to PO items
- [ ] Discrepancies are highlighted for review
- [ ] Manual corrections persist correctly
- [ ] System works without AI (manual fallback)

## Technical Notes

- Use multipart/form-data for file uploads
- Consider OCR fallback for non-text PDFs
- Implement rate limiting for LLM API calls
- Cache extraction results to avoid re-processing
