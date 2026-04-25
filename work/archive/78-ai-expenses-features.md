# Phase 6: AI Expenses

## Goal

Streamline expense management by enabling users to create expenses from receipts
(images/PDFs) and attach receipts to existing records.

## Milestones

### 1. Backend Foundation

- [x] Create `ExpenseReceipt` model and migration
- [x] Create `receipt_extraction.md` prompt for ADK
- [x] Add `parse-receipt` endpoint to `expenses.py`
- [x] Add receipt management endpoints (upload/list/delete)

### 2. Frontend Implementation

- [x] Update `Expense` interface
- [x] Add "Drop Receipt" zone to `ExpenseFormComponent` (Create Mode)
- [x] Implement auto-fill logic (Merchant, Date, Amount, Category)
- [x] Implement "Attach Receipt" for existing expenses (Edit Mode)

### 3. Verification

- [x] Test receipt parsing with various samples
- [x] Verify file attachment workflow
