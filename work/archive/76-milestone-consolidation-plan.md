# Plan: Finalize Milestone 1 & Execute Milestone 2

**Status:** ✅ Complete
**Date:** 2026-01-10 → 2026-01-11

This plan outlines the steps to wrap up the "AI Content Generation" phase
(Milestone 1) and proceed immediately to "Intelligent Purchase Order & Receiving"
(Milestone 2).

## Part 1: Finalize Milestone 1 (AI Content & Media Suite) ✅

**Goal:** Complete the remaining AI and media management features.

### 1. Backend: Product Image Ordering ✅

- [x] Add `order` column to `product_images` table
- [x] Implement `POST /api/v1/products/{product_id}/images/reorder`
- [x] Create Alembic migration

### 2. Frontend: Connect Media Reordering ✅

- [x] Update `ProductFormImageGalleryComponent` with drag-drop reorder API calls
- [x] Persist and reflect new order in UI

### 3. Backend: AI Description Generation ✅

- [x] Add `POST /api/v1/ai/generate-description`
- [x] Uses ADKManager with DescriptionAgent

### 4. Frontend: AI Description Button ✅

- [x] Add "Generate with AI" button next to Description field
- [x] Loading state and textarea population

---

## Part 2: Milestone 2 - Intelligent PO & Receiving ✅

### 1. Backend: Invoice Parser Service ✅

- [x] `InvoiceParserAgent` in `backend/src/services/adk/agents/invoice/`
- [x] Multimodal extraction (PDF, Image, HTML, TXT)
- [x] Returns structured JSON (vendor, items, totals)

### 2. Backend: Unified Parse-Document Endpoint ✅

- [x] `POST /api/v1/purchase-orders/parse-document`
- [x] Smart PO matching by vendor + items
- [x] Returns `mode: "create"` or `mode: "match"`

### 3. Frontend: Invoice Upload & Matching UI ✅

- [x] `InvoiceMatchDialogComponent` - side-by-side comparison
- [x] "Apply Invoice Values" action to update PO costs
- [x] "Different PO" warning dialog with navigation
- [x] i18n translations (EN + ES-MX)

### 4. Configuration ✅

- [x] LLM configured via Settings → AI & Agents
- [x] Uses `gemini-2.0-flash` model

## Resolution

All items completed on 2026-01-11. Unified workflow implemented - single parser
handles both new PO creation and invoice matching against existing POs.

